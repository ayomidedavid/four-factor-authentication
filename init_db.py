import pymysql

def create_db():
    try:
        # Connect to MySQL without specifying a database
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password=''
        )
        cursor = connection.cursor()
        
        # Create the database
        cursor.execute("CREATE DATABASE IF NOT EXISTS four_factor_auth")
        print("Database 'four_factor_auth' checked/created successfully!")
        
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Error creating database: {e}")
        print("Please ensure XAMPP MySQL is running.")

if __name__ == "__main__":
    create_db()
