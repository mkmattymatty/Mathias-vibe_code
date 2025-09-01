from db import get_connection

conn = get_connection()
cursor = conn.cursor()
cursor.execute("SHOW TABLES;")

print("Tables in sdg_app:")
for table in cursor.fetchall():
    print(table[0])

cursor.close()
conn.close()
