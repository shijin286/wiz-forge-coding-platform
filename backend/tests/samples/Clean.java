import java.sql.*;
import java.util.logging.Logger;

public class UserRepository {
    private static final Logger LOG = Logger.getLogger(UserRepository.class.getName());

    public String findName(Connection conn, int id) throws SQLException {
        String sql = "SELECT name FROM users WHERE id = ?";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setInt(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString("name") : null;
            }
        }
    }

    public boolean isAdmin(String role) {
        if ("admin".equals(role)) {
            LOG.info("admin access");
            return true;
        }
        return false;
    }
}
