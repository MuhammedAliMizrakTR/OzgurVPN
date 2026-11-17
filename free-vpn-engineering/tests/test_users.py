import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from users import make_users, select_password


class UserTests(unittest.TestCase):
    def test_distinct_random_credentials(self):
        users = make_users(['owner', 'friend'])
        self.assertEqual([u['name'] for u in users], ['owner', 'friend'])
        self.assertEqual(len({u['password'] for u in users}), 2)
        self.assertTrue(all(len(u['password']) >= 40 for u in users))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'users.json'
            path.write_text(json.dumps(users))
            self.assertEqual(select_password(path, 'friend'), users[1]['password'])
            with self.assertRaises(ValueError):
                select_password(path, 'missing')

    def test_invalid_names(self):
        for names in ([], ['same', 'same'], ['bad/name'], ['']):
            with self.subTest(names=names), self.assertRaises(ValueError):
                make_users(names)


if __name__ == '__main__':
    unittest.main()
