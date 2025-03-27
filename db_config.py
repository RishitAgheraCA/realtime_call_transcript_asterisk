import os
import mysql.connector
from mysql.connector import Error

# Fetch DB credentials from environment variables
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "doalog"),
    "password": os.getenv("DB_PASSWORD", "1234"),
    "database": os.getenv("DB_NAME", "asterisk"),
    "port": "3306"
}

# SQL query to create the table
CREATE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS call_transcripts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lead_id INT NULL,
    original_unique_id VARCHAR(50) NULL,
    unique_id VARCHAR(50) NOT NULL,
    channel_type VARCHAR(50) NULL,
    caller_id INT NULL,
    callee_id VARCHAR(20) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NULL,
    duration INT GENERATED ALWAYS AS (TIMESTAMPDIFF(SECOND, start_time, end_time)) STORED,
    status ENUM('ongoing', 'completed', 'failed') DEFAULT 'ongoing',
    final_transcript TEXT NULL,
    json_data JSON NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def create_database_connection():
    """Establishes a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"]
        )
        if connection.is_connected():
            print("✅ Connected to MySQL Database")
            return connection
    except Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return None

def create_table(connection):
    """Creates the call_transcripts table if it does not exist."""
    try:
        cursor = connection.cursor()
        cursor.execute(CREATE_TABLE_QUERY)
        connection.commit()
        print("✅ Table 'call_transcripts' created successfully (if not exists)")
    except Error as e:
        print(f"❌ Error creating table: {e}")
    finally:
        cursor.close()

def main():
    """Main function to connect to MySQL and create the table."""
    connection = create_database_connection()
    if connection:
        create_table(connection)
        connection.close()
        print("🔌 Connection closed.")

if __name__ == "__main__":
    main()
