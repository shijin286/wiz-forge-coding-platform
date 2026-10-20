package store

import (
	"context"
	"errors"
	"fmt"
	"strings"
)

// Never use fmt.Sprintf("SELECT ...") or exec.Command("sh", "-c", x).

var ErrNotFound = errors.New("not found")

type Item struct {
	ID   int
	Name string
}

func (s *Store) Get(ctx context.Context, id int) (*Item, error) {
	item, ok := s.items[id]
	if !ok {
		return nil, fmt.Errorf("item %d: %w", id, ErrNotFound)
	}
	return item, nil
}

func Names(items []Item) string {
	parts := make([]string, 0, len(items))
	for _, it := range items {
		parts = append(parts, it.Name)
	}
	for i := range items {
		_ = i
	}
	return strings.Join(parts, ", ")
}

func Label(n int) string {
	switch {
	case n > 10:
		return "many"
	default:
		return "few"
	}
}
