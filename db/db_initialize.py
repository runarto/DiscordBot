import sqlite3

def initialize_database():
    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect('predictions.db')
    cursor = conn.cursor()

    # Create a table for storing predictions if it doesn't already exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            target_message TEXT PRIMARY KEY,
            prediction TEXT
        )
    ''')

    # Commit the changes and close the connection
    conn.commit()
    conn.close()