import unittest

import requests
import requests_mock

import main
from main import InvalidHTTPStatusCode

from unittest import mock


class TestReadConfig(unittest.TestCase):
    def test_cfg(self):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        config = main.read_config()
        self.assertIsNotNone(config)
        self.assertEqual("127.0.0.1", config["TCP_SERVICE_ADDRESS"])


class TestTCPConnect(unittest.TestCase):
    @mock.patch('socket.socket')
    def test_tcp_bad_auth(self, mck):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        self.assertRaises(main.TCPAuthenticationError, main.tcp_connect)

    def test_tcp_connect_error(self):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        self.assertRaises(ConnectionRefusedError, main.tcp_connect)


class TestNotify(unittest.TestCase):
    @mock.patch('smtplib.SMTP')
    def test_send_email_ok(self, mock_smtp):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        mock_smtp.starttls.return_value = ""
        mock_smtp.login.return_value = ""
        mock_smtp.sendmail.return_value = ""
        self.assertIsNone(main.notify("test"))


class TestCompareResponses(unittest.TestCase):
    def test_compare(self):
        eq = main.test_response("CLOUDWALK TESTE")
        ne = main.test_response("NOT_EXPECTED")
        self.assertTrue(eq)
        self.assertFalse(ne)


class TestHTTPConnect(unittest.TestCase):
    @requests_mock.Mocker()
    def test_http_timeout(self, request_mock):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        config = main.read_config()
        url = "".join([config["HTTP_SERVICE_ADDRESS"], "?auth=", config["TOKEN"], "&buf=TESTE"])
        request_mock.get(url, exc=requests.exceptions.ReadTimeout)
        response = main.http_connect()
        self.assertEqual("", response)

    @requests_mock.Mocker()
    def test_http_invalid_status_code(self, request_mock):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        config = main.read_config()
        url = "".join([config["HTTP_SERVICE_ADDRESS"], "?auth=", config["TOKEN"], "&buf=TESTE"])
        request_mock.get(url, status_code=999)
        self.assertRaises(InvalidHTTPStatusCode, main.http_connect)

    @requests_mock.Mocker()
    def test_http_ok(self, request_mock):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        config = main.read_config()
        url = "".join([config["HTTP_SERVICE_ADDRESS"], "?auth=", config["TOKEN"], "&buf=TESTE"])
        request_mock.get(url, status_code=200, text="CLOUDWALK TESTE")
        self.assertEqual("CLOUDWALK TESTE", main.http_connect())


class TestHealthy(unittest.TestCase):
    def test_reset_all(self):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        h = main.Healthy()
        h.error()
        h.success()
        self.assertEqual(1, h.ok_counter)
        self.assertEqual(1, h.err_counter)
        h.reset_all()
        self.assertEqual(0, h.ok_counter)
        self.assertEqual(0, h.err_counter)
        self.assertFalse(h.ok)

    def test_ok(self):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        h = main.Healthy()
        h.success()
        self.assertFalse(h.ok)
        h.success()
        self.assertFalse(h.ok)
        h.success()
        self.assertFalse(h.ok)
        h.success()
        self.assertFalse(h.ok)
        h.success()
        self.assertFalse(h.ok)
        h.success()
        self.assertTrue(h.ok)

    def test_success_reset(self):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        h = main.Healthy()
        h.success()
        self.assertEqual(1, h.ok_counter)
        h.success_reset()
        self.assertFalse(h.ok)
        self.assertEqual(0, h.ok_counter)

    def test_error(self):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        h = main.Healthy()
        h.error()
        h.error()
        h.error()
        h.error()
        self.assertRaises(main.ErrorThresholdReached, h.error)

    def test_error_reset(self):
        main.CONFIG_FILE = "./tests/config-tests.yaml"
        h = main.Healthy()
        h.error()
        self.assertEqual(1, h.err_counter)
        h.error_reset()
        self.assertEqual(0, h.err_counter)


class TestTCPService(unittest.TestCase):
    @mock.patch('main.notify')
    def test_tcp_general_error(self, mock_notify):
        main.CONFIG_FILE = "./tests/config-tests-http-test.yaml"
        mock_notify.return_value = ""
        scan = main.Tests()
        type(scan)._RUNNING = mock.PropertyMock(side_effect=[True, False])
        self.assertIsNone(scan.test_tcp())

    @mock.patch('main.notify')
    @mock.patch('main.tcp_connect')
    def test_http_general_tcp_no_recovery(self, mock_http_connect, mock_notify):
        main.CONFIG_FILE = "./tests/config-tests-http-test.yaml"
        mock_notify.return_value = ""
        mock_http_connect.return_value = "CLOUDWALK TESTE"
        scan = main.Tests()
        type(scan)._RUNNING = mock.PropertyMock(side_effect=[True, True, True, False])
        self.assertIsNone(scan.test_tcp())

    @mock.patch('main.notify')
    @mock.patch('main.tcp_connect')
    def test_http_general_tcp_wrong_remote_response(self, mock_http_connect, mock_notify):
        main.CONFIG_FILE = "./tests/config-tests-http-test.yaml"
        mock_notify.return_value = ""
        mock_http_connect.return_value = "CLOUDWALK MOCKED"
        scan = main.Tests()
        type(scan)._RUNNING = mock.PropertyMock(side_effect=[True, False])
        self.assertIsNone(scan.test_tcp())

    @mock.patch('main.notify')
    @mock.patch('main.tcp_connect')
    def test_http_general_tcp_wrong_threshold_reached(self, mock_http_connect, mock_notify):
        main.CONFIG_FILE = "./tests/config-tests-http-test.yaml"
        mock_notify.return_value = ""
        mock_http_connect.return_value = "CLOUDWALK MOCKED"
        scan = main.Tests()
        type(scan)._RUNNING = mock.PropertyMock(side_effect=[True, True, True, True, True, True, False])
        self.assertIsNone(scan.test_tcp())

    @mock.patch('main.notify')
    @mock.patch('main.tcp_connect')
    def test_tcp_chanced_state_to_failed(self, mock_http_connect, mock_notify):
        main.CONFIG_FILE = "./tests/config-tests-http-test.yaml"
        mock_notify.return_value = ""
        mock_http_connect.side_effect = ["CLOUDWALK TESTE",
                                         "CLOUDWALK TESTE",
                                         "CLOUDWALK TESTE",
                                         "CLOUDWALK TESTE",
                                         "CLOUDWALK FALHOU",
                                         "CLOUDWALK FALHOU"
                                         "CLOUDWALK FALHOU"
                                         "CLOUDWALK FALHOU"
                                         "CLOUDWALK FALHOU"]
        scan = main.Tests()
        type(scan)._RUNNING = mock.PropertyMock(side_effect=[True,
                                                             True,
                                                             True,
                                                             True,
                                                             True,
                                                             True,
                                                             True,
                                                             True,
                                                             True,
                                                             False])
        self.assertIsNone(scan.test_tcp())


class TestHTTPService(unittest.TestCase):
    @mock.patch('main.notify')
    def test_http_general_error(self, mock_notify):
        main.CONFIG_FILE = "./tests/config-tests-http-test.yaml"
        mock_notify.return_value = ""
        scan = main.Tests()
        type(scan)._RUNNING = mock.PropertyMock(side_effect=[True, False])
        self.assertIsNone(scan.test_http())

    @mock.patch('main.notify')
    @mock.patch('main.http_connect')
    def test_http_general_http_no_recovery(self, mock_http_connect, mock_notify):
        main.CONFIG_FILE = "./tests/config-tests-http-test.yaml"
        mock_notify.return_value = ""
        mock_http_connect.return_value = "CLOUDWALK TESTE"
        scan = main.Tests()
        type(scan)._RUNNING = mock.PropertyMock(side_effect=[True, True, True, False])
        self.assertIsNone(scan.test_http())

    @mock.patch('main.notify')
    @mock.patch('main.http_connect')
    def test_http_general_http_wrong_remote_response(self, mock_http_connect, mock_notify):
        main.CONFIG_FILE = "./tests/config-tests-http-test.yaml"
        mock_notify.return_value = ""
        mock_http_connect.return_value = "CLOUDWALK MOCKED"
        scan = main.Tests()
        type(scan)._RUNNING = mock.PropertyMock(side_effect=[True, False])
        self.assertIsNone(scan.test_http())

    @mock.patch('main.notify')
    @mock.patch('main.http_connect')
    def test_http_general_http_wrong_threshold_reached(self, mock_http_connect, mock_notify):
        main.CONFIG_FILE = "./tests/config-tests-http-test.yaml"
        mock_notify.return_value = ""
        mock_http_connect.return_value = "CLOUDWALK MOCKED"
        scan = main.Tests()
        type(scan)._RUNNING = mock.PropertyMock(side_effect=[True, True, True, True, True, True, False])
        self.assertIsNone(scan.test_http())

    @mock.patch('main.notify')
    @mock.patch('main.http_connect')
    def test_http_chanced_state_to_failed(self, mock_http_connect, mock_notify):
        main.CONFIG_FILE = "./tests/config-tests-http-test.yaml"
        mock_notify.return_value = ""
        mock_http_connect.side_effect = ["CLOUDWALK TESTE",
                                         "CLOUDWALK TESTE",
                                         "CLOUDWALK TESTE",
                                         "CLOUDWALK TESTE",
                                         "CLOUDWALK FALHOU",
                                         "CLOUDWALK FALHOU"
                                         "CLOUDWALK FALHOU"
                                         "CLOUDWALK FALHOU"
                                         "CLOUDWALK FALHOU"]
        scan = main.Tests()
        type(scan)._RUNNING = mock.PropertyMock(side_effect=[True,
                                                             True,
                                                             True,
                                                             True,
                                                             True,
                                                             True,
                                                             True,
                                                             True,
                                                             True,
                                                             False])
        self.assertIsNone(scan.test_http())
