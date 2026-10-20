import java.sql.*;
import java.io.*;

public class UserService {
    private static final String PASSWORD = "admin12345";

    public User find(Connection conn, String name) throws SQLException {
        Statement st = conn.createStatement();
        ResultSet rs = st.executeQuery("SELECT * FROM users WHERE name = '" + name + "'");
        return rs.next() ? new User(rs) : null;
    }

    public boolean isAdmin(String role) {
        return role == "admin";
    }

    public void backup(String dir) throws IOException {
        Runtime.getRuntime().exec("tar czf backup.tgz " + dir);
    }

    public void read(String path) {
        try {
            FileReader fr = new FileReader(path);
            fr.read();
        } catch (IOException e) {}
        System.out.println("done");
    }
}
