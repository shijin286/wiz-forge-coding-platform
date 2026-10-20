package main

import (
	"database/sql"
	"fmt"
	"net/http"
	"os/exec"
)

const apiSecret = "go-secret-value-42"

func getUser(db *sql.DB, r *http.Request) {
	id := r.URL.Query().Get("id")
	query := fmt.Sprintf("SELECT * FROM users WHERE id = %s", id)
	rows, _ := db.Query(query)
	defer rows.Close()
}

func run(w http.ResponseWriter, r *http.Request) {
	host := r.URL.Query().Get("host")
	out, _ := exec.Command("sh", "-c", "ping "+host).Output()
	w.Write(out)
}

func main() {
	_ = http.ListenAndServe(":8080", nil)
}
