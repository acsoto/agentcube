# 在 Kubernetes worker 上跑 Kuasar 和 AgentCube

目标是在一个节点上完成一次真实会话：SDK 创建会话，节点给 VM 分配资源，通过 Router 在 VM 内执行命令，删除后资源回收。已有实验环境的同事直接看第 1 节；需要在另一台机器搭环境，再从第 2 节开始。

## 1. 先看已有集群

2026-11-12 跑通的环境是 Apple M1 Max 上的一个本地 K3s 集群。控制面运行在 Docker 里，唯一的 worker 是 QEMU 启动的 Debian。Kuasar 在这个 worker 内使用 KVM 和 Cloud Hypervisor 启动用户 VM。PicoD 位于用户 VM 内。这里有两层虚拟机，QEMU 的用途是提供 Linux worker。已有可使用 KVM 的 Linux 实验节点可以直接充当 worker。

在有集群访问权限的终端检查：

```sh
kubectl get nodes -o wide
kubectl get sandboxpool -o wide
kubectl -n sandbox-system get pods -o wide
kubectl describe sandboxpool placeholder-e2e-poolset-0
```

在 worker 上检查：

```sh
uname -m
ls -l /dev/kvm
sudo /opt/kuasar/bin/node-ctl resource list --socket /run/node-ctl/node-ctl.sock
```

验收前应同时看到 Node Ready、Pool Ready、placeholder Pod Running。本实验在空闲节点上返回的资源列表可以是 JSON null 或空数组。**2026-11-16 复查**时，Node Ready、placeholder Running、node-ctl 可达，但 Pool 为 Degraded，具体条件为 PlaceholderAgentHealthy=False / LeaseExpired。遇到这个现象，先看 agent 服务、日志及它能否续租，再确认 Pool 恢复 Ready。原实验采用 systemd 启动 agent，可用 `systemctl status lab-agent` 和 `journalctl -u lab-agent -n 80`。这里记录的完整 SDK 成功结果来自 11 月 12 日。

## 2. 需要自建 worker 时，如何用 QEMU

下面的参考命令针对实验用的 Apple Silicon + Homebrew QEMU 11.1.3。准备 Debian 13 **generic ARM64 cloud image**、SSH 密钥，以及 macOS 自带的 hdiutil。generic 内核是上次成功提供 /dev/kvm 的选择。以下在一个新实验目录运行；先将下载的 Debian 镜像放为 debian-generic-arm64.qcow2。每个 worker 用独立磁盘、主机名、cloud-init instance-id 和宿主机转发端口。

```sh
ssh-keygen -t ed25519 -f ./lab-key -N ''
mkdir seed
printf 'instance-id: pool-a-01\nlocal-hostname: pool-a\n' > seed/meta-data
printf '#cloud-config\nuser: debian\nssh_authorized_keys:\n  - %s\n' "$(cat lab-key.pub)" > seed/user-data
hdiutil makehybrid -iso -joliet -default-volume-name cidata -o cidata.iso seed
cp debian-generic-arm64.qcow2 worker.qcow2
qemu-img resize worker.qcow2 14G
firmware="$(brew --prefix)/share/qemu"
cp "$firmware/edk2-arm-vars.fd" nvram.fd
qemu-system-aarch64 \
  -machine virt,virtualization=on,gic-version=3 -cpu cortex-a72 \
  -accel tcg,thread=multi -smp 4 -m 4500 \
  -drive "if=pflash,format=raw,readonly=on,file=$firmware/edk2-aarch64-code.fd" \
  -drive if=pflash,format=raw,file=nvram.fd \
  -drive if=virtio,format=qcow2,file=worker.qcow2 \
  -drive if=virtio,format=raw,readonly=on,file=cidata.iso \
  -netdev user,id=n,hostfwd=tcp:127.0.0.1:19222-:22,hostfwd=tcp:127.0.0.1:18945-:18945 \
  -device virtio-net-pci,netdev=n,romfile= -display none -serial file:console.log \
  -monitor none -daemonize -pidfile qemu.pid
```

等待 cloud-init 完成，再用 `ssh -p 19222 -i ./lab-key debian@127.0.0.1` 登录，验证 /dev/kvm 和内核版本。端口已被原实验占用时换一组宿主端口。这里的命令根据运行中的 QEMU 参数整理，新建镜像流程没有再次从零演练。TCG 环境用于功能验证，其时延不代表生产节点。

## 3. 让 Kuasar 和占位 Pod 用同一个 worker

1. **加入集群。** 原实验在 Debian 内运行 K3s agent，注册为 pool-vm，参数包括 `--server https://10.0.2.2:16443 --token-file /opt/pool-lab/token --node-name pool-vm --node-label sandbox-pool.io/pool-node=true`。10.0.2.2 是本例 QEMU 用户网络通往宿主机的地址；其他集群要填其实际可达的 API 地址，并使用该集群的入群方式。已有 worker 只需确认 Pool 的节点选择标签。
2. **准备 Pool。** 使用相匹配的 Pool CRD、controller、placeholder-agent 和 containerd-shim-placeholder-v2（实验源码 e440730）。在节点 containerd 注册 handler placeholder、runtime_type 为 io.containerd.placeholder.v2，创建对应 RuntimeClass 和 SandboxPoolSet。实验选择上述标签，资源为 3 CPU、1800 MiB。K3s v1.35.5+k3s1 内置 containerd 2.2.3 在此 shim 上报 unsupported protocol；仅在专用实验 VM 中使用 containerd 2.3.1 并补齐 pause 镜像后，placeholder 才 Running。已有集群应先在专用 worker 验证版本组合。
3. **准备节点运行时。** 实验使用 Kuasar release-v0.1.13 的 ARM64 工件，包括 node-ctl、sandbox-ctl、connector-ctl、e2b-key-ctl、cloud-hypervisor、vmlinux 和 sandbox-runtime.bundle。配置 TAP vswitch、guest 内核和本地模板位置。实验中 8 个 switch 端口全部被预留，改为 64 后 VM 才能接入。PicoD 根文件系统镜像、模板 ID、192 MiB 可写 overlay 和适配器配置见[同目录实验报告](README.md)。
4. **启动节点服务。** placeholder-agent 根据 Pool 预算生成 /run/node-ctl/conductor.yaml。先建状态目录 /opt/pool-lab/state 和运行目录 /run/ksb，再启动 conductor。等控制 socket 存在，启动使用同一 socket 的 proxy。原实验用 systemd 分别托管以下两个前台命令；从两个终端调试也可分别启动。

```sh
node-ctl conductor serve --config /run/node-ctl/conductor.yaml
node-ctl proxy serve --config /opt/pool-lab/proxy.yaml
```

5. **接入 AgentCube。** 按[实验报告](README.md)启动共用 Redis 的 Router 和适配器，准备节点 API key、PicoD 模板 ID、Router 签名密钥以及对应公钥。实验地址是 conductor 18083、proxy 18084、适配器 18090；三者监听节点 loopback。Router 与适配器共享节点网络，才能访问 Redis 中登记的本机转发端口。客户端通过 QEMU 转发访问 Router，通过 SSH 本地转发把适配器端口映射到宿主机 19090。

## 4. 验收和复用边界

在安装了本仓 sdk-python 的环境中运行。pool-vm 是你配置的 SSH 别名，需要允许在专用节点无交互读取资源 socket。

```sh
ROUTER_URL=http://127.0.0.1:18945 WORKLOAD_MANAGER_URL=http://127.0.0.1:19090 \
  python example/kuasar-pool/verify.py --ssh pool-vm
```

对照三个结果：节点 reservation 的 sandbox ID 等于 SDK 会话 ID；在 guest 执行 echo hello，返回 hello 和退出码 0；删除后 reservation 清空，旧会话被拒绝。11 月 12 日验收观察到单个会话预留 384 MiB、1000m CPU。

**扩到两节点时先解决网络。** 两个独立的 QEMU 用户网络默认可以给 guest 相同的内部 IP。仅改节点名和 SSH 转发端口，不足以让 kubelet、集群网络以及 Router 分清并到达两个 worker。需要唯一、可路由的节点地址或等效的网络设计，每个 Pool 的 conductor/proxy 也要有明确可达的入口。单节点实验的 loopback 配置不能原样验证跨节点寻址。双节点和 kind worker 内的 KVM 均未在本次实验中验证。
