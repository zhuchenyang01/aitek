import unittest

from app.utils.json_parser import parse_json_array


class JsonParserTests(unittest.TestCase):
    def test_parse_plain_json_array(self):
        text = '[{"模块":"登录","功能点":"用户名密码登录"}]'
        result = parse_json_array(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['模块'], '登录')

    def test_parse_json_with_prefix(self):
        text = '说明如下：[{"模块":"订单","功能点":"创建订单"}]'
        result = parse_json_array(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['功能点'], '创建订单')

    def test_parse_single_quotes(self):
        text = "[{'模块':'支付','功能点':'微信支付'}]"
        result = parse_json_array(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['模块'], '支付')

    def test_parse_invalid_returns_empty(self):
        self.assertEqual(parse_json_array('not json'), [])

    def test_parse_truncated_pretty_json(self):
        text = (
            '[\n'
            '  {"模块": "登录", "功能点": "账号密码登录"},\n'
            '  {"模块": "融担接口-授信申请", "功能点": "融担授信申请接口为'
        )
        result = parse_json_array(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['模块'], '登录')

    def test_parse_code_fence(self):
        text = '```json\n[{"模块":"订单","功能点":"下单"}]\n```'
        result = parse_json_array(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['模块'], '订单')


if __name__ == '__main__':
    unittest.main()
