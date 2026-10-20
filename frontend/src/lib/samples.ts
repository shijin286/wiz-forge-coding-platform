// Generated from backend/tests/samples - deliberately flawed snippets for trying out the reviewer.
// The backend test suite asserts which issues each one contains, so keep the two in sync.
export const SAMPLES: Record<string, { title: string; code: string }> = {
  python: {
    title: "orders/service.py",
    code: "import os\nimport pickle\nimport subprocess\nimport requests\n\nAPI_TOKEN = \"tok_live_9f8e7d6c5b4a\"\n\n\ndef fetch_user(cur, user_id):\n    cur.execute(\"SELECT * FROM users WHERE id = %s\" % user_id)\n    return cur.fetchone()\n\n\ndef add_item(item, cart=[]):\n    cart.append(item)\n    return cart\n\n\ndef download(url):\n    return requests.get(url, verify=False).text\n\n\ndef restore(blob):\n    try:\n        return pickle.loads(blob)\n    except:\n        pass\n\n\ndef archive(name):\n    subprocess.run(\"zip backup.zip \" + name, shell=True)\n\n\ndef is_admin(user):\n    if user == None:\n        return False\n    return user.role == \"admin\"\n",
  },
  javascript: {
    title: "server/routes.js",
    code: "const express = require(\"express\");\nconst { exec } = require(\"child_process\");\nconst app = express();\n\nconst DB_PASSWORD = \"p@ssw0rd-prod-2024\";\n\napp.get(\"/user\", (req, res) => {\n  db.query(`SELECT * FROM users WHERE id = ${req.query.id}`, (err, rows) => {\n    res.send(rows);\n  });\n});\n\napp.get(\"/ping\", (req, res) => {\n  exec(`ping -c 1 ${req.query.host}`, (err, out) => res.send(out));\n});\n\nfunction renderName(name) {\n  document.getElementById(\"greeting\").innerHTML = \"Hello \" + name;\n}\n\nfunction check(a, b) {\n  if (a == b) {\n    console.log(\"equal\");\n  }\n  try {\n    JSON.parse(b);\n  } catch (e) {}\n}\n\nvar counter = 0;\nsetTimeout(\"counter++\", 100);\neval(userCode);\n",
  },
  typescript: {
    title: "ui/profile.ts",
    code: "interface User {\n  id: number;\n  name: string;\n  isAdmin?: boolean;\n}\n\nconst apiKey: string = \"sk_live_51HxYzAbCdEfGh\";\n\nexport function render(user: User): void {\n  const el = document.querySelector(\"#profile\")!;\n  el.innerHTML = `<h1>${user.name}</h1>`;\n}\n\nexport async function load(id: string): Promise<User> {\n  const res = await fetch(\"/api/users/\" + id);\n  return (await res.json()) as any;\n}\n\nexport function compare(a: any, b: any): boolean {\n  return a == b;\n}\n\nexport function run(expr: string) {\n  return new Function(\"return \" + expr)();\n}\n",
  },
  java: {
    title: "UserService.java",
    code: "import java.sql.*;\nimport java.io.*;\n\npublic class UserService {\n    private static final String PASSWORD = \"admin12345\";\n\n    public User find(Connection conn, String name) throws SQLException {\n        Statement st = conn.createStatement();\n        ResultSet rs = st.executeQuery(\"SELECT * FROM users WHERE name = '\" + name + \"'\");\n        return rs.next() ? new User(rs) : null;\n    }\n\n    public boolean isAdmin(String role) {\n        return role == \"admin\";\n    }\n\n    public void backup(String dir) throws IOException {\n        Runtime.getRuntime().exec(\"tar czf backup.tgz \" + dir);\n    }\n\n    public void read(String path) {\n        try {\n            FileReader fr = new FileReader(path);\n            fr.read();\n        } catch (IOException e) {}\n        System.out.println(\"done\");\n    }\n}\n",
  },
  cpp: {
    title: "tools/cleanup.cpp",
    code: "#include <iostream>\n#include <cstring>\n#include <cstdlib>\nusing namespace std;\n\nconst char* secret_key = \"hardcoded-secret-123\";\n\nvoid greet(const char* name) {\n    char buffer[16];\n    strcpy(buffer, name);\n    cout << \"Hello \" << buffer << endl;\n}\n\nvoid cleanup(const string& dir) {\n    string cmd = \"rm -rf \" + dir;\n    system(cmd.c_str());\n}\n\nint* makeArray(int n) {\n    int* arr = new int[n];\n    return arr;\n}\n\nint main(int argc, char** argv) {\n    greet(argv[1]);\n    int* data = makeArray(10);\n    cleanup(argv[2]);\n    return 0;\n}\n",
  },
  c: {
    title: "auth/login.c",
    code: "#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\n\n#define PASSWORD \"letmein123\"\n\nint login(void) {\n    char input[32];\n    printf(\"Password: \");\n    gets(input);\n    return strcmp(input, PASSWORD) == 0;\n}\n\nvoid log_message(const char* user, const char* msg) {\n    char line[64];\n    sprintf(line, \"%s: %s\", user, msg);\n    printf(line);\n}\n\nint main(void) {\n    char* buf = malloc(100);\n    strcat(buf, \"data\");\n    if (login()) {\n        system(\"cat /etc/shadow\");\n    }\n    return 0;\n}\n",
  },
  go: {
    title: "api/handlers.go",
    code: "package main\n\nimport (\n\t\"database/sql\"\n\t\"fmt\"\n\t\"net/http\"\n\t\"os/exec\"\n)\n\nconst apiSecret = \"go-secret-value-42\"\n\nfunc getUser(db *sql.DB, r *http.Request) {\n\tid := r.URL.Query().Get(\"id\")\n\tquery := fmt.Sprintf(\"SELECT * FROM users WHERE id = %s\", id)\n\trows, _ := db.Query(query)\n\tdefer rows.Close()\n}\n\nfunc run(w http.ResponseWriter, r *http.Request) {\n\thost := r.URL.Query().Get(\"host\")\n\tout, _ := exec.Command(\"sh\", \"-c\", \"ping \"+host).Output()\n\tw.Write(out)\n}\n\nfunc main() {\n\t_ = http.ListenAndServe(\":8080\", nil)\n}\n",
  },
  other: {
    title: "config/setup.rb",
    code: "# TODO: move credentials out of source\npassword = \"rubyS3cretValue\"\nAKIAIOSFODNN7EXAMPLE = \"aws\"\ndef greet(name)\n  puts \"Hello #{name}\"\nend\n",
  },
};
