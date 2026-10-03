"""
Export MySQL database schema and data to database_dump.sql.
Can be imported directly into XAMPP phpMyAdmin or MySQL CLI on any machine.
"""
import os
import pymysql

def export():
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='12345678',
        db='community_parking_db',
        charset='utf8mb4'
    )
    cur = conn.cursor()

    tables = ['users', 'parking_spaces', 'parking_images', 'bookings', 'reviews', 'notifications', 'audit_logs']

    sql_lines = [
        "-- ============================================================================",
        "-- COMMUNITY PARKING SYSTEM — Full MySQL Database Dump (Schema + Data)",
        "-- Target: XAMPP MySQL / MariaDB / phpMyAdmin",
        "-- ============================================================================",
        "",
        "CREATE DATABASE IF NOT EXISTS `community_parking_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "USE `community_parking_db`;",
        "",
        "SET FOREIGN_KEY_CHECKS = 0;",
        ""
    ]

    for t in tables:
        cur.execute(f"SHOW CREATE TABLE `{t}`")
        res = cur.fetchone()
        create_stmt = res[1]
        sql_lines.append(f"DROP TABLE IF EXISTS `{t}`;")
        sql_lines.append(create_stmt + ";")
        sql_lines.append("")

        cur.execute(f"SELECT * FROM `{t}`")
        rows = cur.fetchall()
        if rows:
            cur.execute(f"DESCRIBE `{t}`")
            cols = [f"`{r[0]}`" for r in cur.fetchall()]
            cols_str = ", ".join(cols)

            insert_vals = []
            for r in rows:
                val_strs = []
                for v in r:
                    if v is None:
                        val_strs.append("NULL")
                    elif isinstance(v, (int, float)):
                        val_strs.append(str(v))
                    elif isinstance(v, bool):
                        val_strs.append("1" if v else "0")
                    else:
                        escaped = str(v).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
                        val_strs.append(f"'{escaped}'")
                insert_vals.append("(" + ", ".join(val_strs) + ")")

            sql_lines.append(f"INSERT INTO `{t}` ({cols_str}) VALUES")
            sql_lines.append(",\n".join(insert_vals) + ";")
            sql_lines.append("")

    sql_lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    sql_lines.append("")

    out_file = os.path.join(os.path.dirname(__file__), "database_dump.sql")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))

    print(f"Exported successfully to {out_file} ({os.path.getsize(out_file)} bytes)")
    conn.close()

if __name__ == "__main__":
    export()
