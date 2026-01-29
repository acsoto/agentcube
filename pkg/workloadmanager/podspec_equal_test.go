package workloadmanager

import (
	"reflect"
	"testing"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
)

func TestPodSpecEqual(t *testing.T) {
	tests := []struct {
		name string
		a    corev1.PodSpec
		b    corev1.PodSpec
		want bool
	}{
		{
			name: "empty specs",
			a:    corev1.PodSpec{},
			b:    corev1.PodSpec{},
			want: true,
		},
		{
			name: "identical simple specs",
			a: corev1.PodSpec{
				Containers: []corev1.Container{{Name: "c1", Image: "img1"}},
			},
			b: corev1.PodSpec{
				Containers: []corev1.Container{{Name: "c1", Image: "img1"}},
			},
			want: true,
		},
		{
			name: "different images",
			a: corev1.PodSpec{
				Containers: []corev1.Container{{Name: "c1", Image: "img1"}},
			},
			b: corev1.PodSpec{
				Containers: []corev1.Container{{Name: "c1", Image: "img2"}},
			},
			want: false,
		},
		{
			name: "different container counts",
			a: corev1.PodSpec{
				Containers: []corev1.Container{{Name: "c1"}},
			},
			b: corev1.PodSpec{
				Containers: []corev1.Container{{Name: "c1"}, {Name: "c2"}},
			},
			want: false,
		},
		{
			name: "resources equal",
			a: corev1.PodSpec{
				Containers: []corev1.Container{{
					Resources: corev1.ResourceRequirements{
						Requests: corev1.ResourceList{corev1.ResourceCPU: resource.MustParse("1")},
					},
				}},
			},
			b: corev1.PodSpec{
				Containers: []corev1.Container{{
					Resources: corev1.ResourceRequirements{
						Requests: corev1.ResourceList{corev1.ResourceCPU: resource.MustParse("1000m")},
					},
				}},
			},
			want: true, // Quantity.Equal handles 1 vs 1000m
		},
		{
			name: "resources unequal",
			a: corev1.PodSpec{
				Containers: []corev1.Container{{
					Resources: corev1.ResourceRequirements{
						Requests: corev1.ResourceList{corev1.ResourceCPU: resource.MustParse("1")},
					},
				}},
			},
			b: corev1.PodSpec{
				Containers: []corev1.Container{{
					Resources: corev1.ResourceRequirements{
						Requests: corev1.ResourceList{corev1.ResourceCPU: resource.MustParse("2")},
					},
				}},
			},
			want: false,
		},
		{
			name: "map field equal",
			a: corev1.PodSpec{
				NodeSelector: map[string]string{"k": "v"},
			},
			b: corev1.PodSpec{
				NodeSelector: map[string]string{"k": "v"},
			},
			want: true,
		},
		{
			name: "map field unequal",
			a: corev1.PodSpec{
				NodeSelector: map[string]string{"k": "v"},
			},
			b: corev1.PodSpec{
				NodeSelector: map[string]string{"k": "v2"},
			},
			want: false,
		},
        {
            name: "nil map vs empty map",
            a: corev1.PodSpec{NodeSelector: nil},
            b: corev1.PodSpec{NodeSelector: map[string]string{}},
            want: true, // Semantically equal? My generated code: len(a) != len(b). len(nil) is 0. len(empty) is 0. So equal.
            // Loop: nil loop 0 times. empty loop 0 times. Returns true.
            // reflect.DeepEqual(nil, empty) is false.
            // My code handles them as equal if they have same content (empty).
            // This is arguably BETTER than reflect.DeepEqual for K8s.
        },
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := PodSpecEqual(tt.a, tt.b); got != tt.want {
				t.Errorf("PodSpecEqual() = %v, want %v", got, tt.want)
			}

            // Also compare with reflect.DeepEqual for cases where we expect strict equality
            // Except for "resources equal" (Quantity 1 vs 1000m) where reflect fails but we succeed.
            if tt.name != "resources equal" && tt.name != "nil map vs empty map" {
                if gotReflect := reflect.DeepEqual(tt.a, tt.b); gotReflect != tt.want {
                     t.Logf("reflect.DeepEqual mismatch for %s: got %v, want %v", tt.name, gotReflect, tt.want)
                }
            }
		})
	}
}
