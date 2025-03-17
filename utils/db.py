import os
import logging
import psycopg2
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # logging.FileHandler('database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database configuration
DB_URL = os.getenv('SUPABASE_URL')


def get_db_connection():
    """Get a PostgreSQL connection"""
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False  # Use transactions
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise


def execute_query(query, params=None):
    """Execute a SQL query and return results"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                return cur.fetchall()
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Query execution error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


def get_companies():
    """Get list of companies from the database"""
    try:
        query = """
            SELECT name, ticker
            FROM companies 
            WHERE name IS NOT NULL 
            ORDER BY name;
        """
        results = execute_query(query)
        return [row for row in results]
    except Exception as e:
        logger.error(f"Error fetching companies: {str(e)}")
        raise


# if __name__ == "__main__":
#     print(get_companies())
