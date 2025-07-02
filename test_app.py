import unittest
from testwhisper import hash_password, add_user, login_user, save_summary, c, conn

class TestWhisperApp(unittest.TestCase):
    def test_hash_password(self):
        password = "asdfasdf"
        hashed = hash_password(password)
        self.assertNotEqual(hashed, password)
    
    def test_add_user(self):
        add_user("warren", "asdfasdf")
        c.execute('SELECT * FROM userstable WHERE username=?', ("warren",))
        user = c.fetchone()
        self.assertIsNotNone(user)
    
    def test_login_user(self):
        add_user("warren", "asdfasdf")
        user = login_user("warren", "asdfasdf")
        self.assertIsNotNone(user)

    def test_save_summary(self):
        add_user("warren", "asdfasdf")
        save_summary("warren", "Test Title", "Hello, my name is warren and I like to party", "tag1,tag2")
        c.execute('SELECT * FROM summaries WHERE username=?', ("warren",))
        summary = c.fetchone()
        self.assertIsNotNone(summary)

if __name__ == '__main__':
    unittest.main()