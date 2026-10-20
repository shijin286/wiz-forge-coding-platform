package main

import (
	"database/sql"
	"fmt"
	"net/http"
	"os/exec"
)

func getUser(db *sql.DB, id string) (string, error) {
	var name string
	err := db.QueryRow("SELECT name FROM users WHERE id = $1", id).Scan(&name)
	if err != nil {
		return "", fmt.Errorf("get user: %w", err)
	}
	return name, nil
}

func ping(host string) ([]byte, error) {
	return exec.Command("ping", "-c", "1", host).Output()
}

func main() {
	for _, port := range []string{":8080"} {
		if err := http.ListenAndServe(port, nil); err != nil {
			fmt.Println(err)
		}
	}
}
