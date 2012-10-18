import unittest

class TestDialect(unittest.TestCase):
    def runTest(self):
        from sqlalchemy import create_engine
        engine = create_engine('pymysql://root@localhost/test')
        self.assertEqual(engine.dialect.name, 'mysql')
        self.assertEqual(engine.driver, 'pymysql')

class TestDialectAsDefault(unittest.TestCase):
    def runTest(self):
        import pymysql_sa
        pymysql_sa.make_default_mysql_dialect()
        from sqlalchemy import create_engine
        engine = create_engine('mysql://root@localhost/test')
        self.assertEqual(engine.dialect.name, 'mysql')
        self.assertEqual(engine.driver, 'pymysql')

all_tests = unittest.TestSuite([TestDialect(), TestDialectAsDefault()])

if __name__ == "__main__":
    unittest.main()
