const express = require("express");
const { exec } = require("child_process");
const app = express();

const DB_PASSWORD = "p@ssw0rd-prod-2024";

app.get("/user", (req, res) => {
  db.query(`SELECT * FROM users WHERE id = ${req.query.id}`, (err, rows) => {
    res.send(rows);
  });
});

app.get("/ping", (req, res) => {
  exec(`ping -c 1 ${req.query.host}`, (err, out) => res.send(out));
});

function renderName(name) {
  document.getElementById("greeting").innerHTML = "Hello " + name;
}

function check(a, b) {
  if (a == b) {
    console.log("equal");
  }
  try {
    JSON.parse(b);
  } catch (e) {}
}

var counter = 0;
setTimeout("counter++", 100);
eval(userCode);
