import logging
import smtplib
import socket
import ssl
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests
import yaml

CONFIG_FILE = "./config.yaml"
TEST_TEXT = "TESTE"


class TCPAuthenticationError(Exception):
    pass


class TCPErrorSendingMessage(Exception):
    pass


class InvalidHTTPStatusCode(Exception):
    pass


class ErrorThresholdReached(Exception):
    pass


def write_http_response():
    """
    returns the text used on http endpoint.
    not the requirements, is ugly.
    a better approach is use memcache...
    :return: bytes
    """
    text = list()
    if HTTP_FAILED:
        text.append("[ ] - HTTP OK")
    else:
        text.append("[X] - HTTP OK")

    if TCP_FAILED:
        text.append("[ ] - TCP OK")
    else:
        text.append("[X] - TCP OK")

    return "\n".join(text).encode()


def read_config():
    """
    reads the config file
    :return: dict
    """
    with open(CONFIG_FILE, "r") as cf:
        return yaml.safe_load(cf)


def tcp_connect():
    """
    connect at tcp service, auth and get the text on socket.
    if auth fail an error will be raised.
    we read 15 bytes (the size of string CLOUDWALK TESTE)
    if a timeout occurs, an empty text will be returned
    :return: string
    """

    config = read_config()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(config["TIMEOUT"])
    try:
        s.connect((config["TCP_SERVICE_ADDRESS"], config["TCP_SERVICE_PORT"]))
    except BaseException as connect_error:
        raise connect_error
    s.send("auth {}\n".format(config["TOKEN"]).encode())
    auth_text = s.recv(7).decode()
    log.debug("Auth Text: {}".format(auth_text))
    if auth_text != "auth ok":
        raise TCPAuthenticationError
    s.send(TEST_TEXT.encode())
    try:
        # reading an /n and ignoring
        s.recv(2)
        # reading the message
        echo_text = s.recv(15).decode()
    except socket.timeout as socket_timeout:
        log.error(socket_timeout)
        log.error("error writing message on socket")
        return ""
    s.close()
    log.debug(echo_text)
    return echo_text


def notify(message):
    """
    send a email message
    :param message: string
    :return: None
    """
    config = read_config()
    to = ", ".join(config["SMTP"]["TO"])
    sender = "monit@monit.com"
    mailmsg = f"""\
Subject: Monitoring
To: {to}
From: {sender}
Subject: {message}

{message}"""
    ctx = ssl.create_default_context()
    with smtplib.SMTP(config["SMTP"]["HOST"], config["SMTP"]["PORT"]) as server:
        server.starttls(context=ctx)
        server.login(config["SMTP"]["USERNAME"], config["SMTP"]["PASSWORD"])
        server.sendmail(sender, to, mailmsg)
    log.debug(mailmsg)


def test_response(remote_message):
    """
    test if the remote message is equal as expected
    :param remote_message: string
    :return: bool
    """
    log.debug(remote_message.encode())
    log.debug("remote: {}".format(remote_message))
    log.debug("expected: CLOUDWALK {}".format(TEST_TEXT))
    log.debug(remote_message == "CLOUDWALK {}".format(TEST_TEXT))
    return remote_message == "CLOUDWALK {}".format(TEST_TEXT)


def http_connect():
    """
    make an http get on http service and parses the output
    if a timeout occurs, an empty text will be returned
    status codes != 200 will be considered an error
    :return: string
    """
    config = read_config()
    params = {
        "auth": config["TOKEN"],
        "buf": TEST_TEXT
    }
    try:
        r = requests.get(url=config["HTTP_SERVICE_ADDRESS"], params=params, timeout=config["TIMEOUT"])
    except requests.exceptions.ReadTimeout:
        log.error("http timeout")
        return ""
    if r.status_code != 200:
        raise InvalidHTTPStatusCode("Returned Status Code: {}".format(r.status_code))
    return r.text.strip()


class Healthy:
    """
    this class helps to determine if a service is healthy or not
    """
    err_counter = 0
    ok = False
    ok_counter = 0
    notify = True

    def still_notified(self):
        """
        method used to mark if a notification was sent
        :return: None
        """
        self.notify = False

    def enable_notify(self):
        """
        method used to mark if a notification was sent
        :return:
        """
        self.notify = True

    def error(self):
        """
        mark an error
        if the UNHEALTHY_THRESHOLD was reached, an error will be raised
        :return: None
        """
        config = read_config()
        log.debug("err counter: {}".format(self.err_counter))
        if self.err_counter >= config["UNHEALTHY_THRESHOLD"]:
            raise ErrorThresholdReached
        self.err_counter += 1

    def error_reset(self):
        """
        reset the error counter
        :return: None
        """
        self.err_counter = 0

    def success(self):
        """
        mark a success
        this method will mark the 'ok' when the HEALTHY_THRESHOLD will be reached
        :return: None
        """
        config = read_config()
        if self.ok_counter <= config["HEALTHY_THRESHOLD"]:
            log.debug("ok counter <= config. config: {} ok counter: {}".format(config["HEALTHY_THRESHOLD"],
                                                                               self.ok_counter))
            self.ok = False
            self.ok_counter += 1
        else:
            log.debug("ok counter > config. config: {} ok counter: {}".format(config["HEALTHY_THRESHOLD"],
                                                                              self.ok_counter))
            self.ok_counter += 1
            if self.ok_counter >= config["HEALTHY_THRESHOLD"]:
                self.ok = True

    def success_reset(self):
        """
        reset the success counter and ok
        :return: None
        """
        self.ok = False
        self.ok_counter = 0

    def reset_all(self):
        """
        reset all counters (errors and success)
        :return: None
        """
        self.ok = False
        self.ok_counter = 0
        self.err_counter = 0


def wait_interval():
    """
    sleep for X times
    :return:
    """
    config = read_config()
    log.debug("Sleeping for: {}s".format(config["CHECK_INTERVAL"]))
    time.sleep(config["CHECK_INTERVAL"])


class Tests:
    """
    class to start the tests
    """
    # variable used only for tests purposes
    _RUNNING = True

    def test_tcp(self):
        """
        make the dirty job to test the returned messages from tcp socket.
        it will check if the response was ok or not.
        :return: None
        """
        global TCP_FAILED
        h = Healthy()
        last_ok = False
        while self._RUNNING:
            try:
                if test_response(tcp_connect()):
                    log.debug("test response OK")
                    h.success()
                    if last_ok is False and h.ok is True:
                        log.debug("tcp service recovered")
                        notify("TCP OK")
                        TCP_FAILED = False
                        h.enable_notify()
                    last_ok = h.ok
                    h.error_reset()
                    wait_interval()
                else:
                    log.debug("wrong response")
                    try:
                        h.error()
                    except ErrorThresholdReached:
                        log.error("too many wrong remote responses")
                        if h.notify:
                            notify("TCP Error - too many wrong remote responses")
                            h.still_notified()
                        TCP_FAILED = True
                        h.reset_all()
                    if last_ok is False and h.ok is False:
                        log.debug("http service changed to false")
                        if h.notify:
                            notify("TCP Error")
                            h.still_notified()
                        # global TCP_FAILED
                        TCP_FAILED = True
                        h.reset_all()
                    last_ok = False
                    wait_interval()
            except BaseException as general_error:
                h.reset_all()
                log.error(general_error)
                TCP_FAILED = True
                wait_interval()

    def test_http(self):
        """
        make the dirty job to test the returned messages from http get.
        it will check if the response was ok or not.
        :return: None
        """
        h = Healthy()
        last_ok = False
        global HTTP_FAILED
        while self._RUNNING:
            try:
                if test_response(http_connect()):
                    log.debug("test response OK")
                    h.success()
                    if last_ok is False and h.ok is True:
                        log.debug("http service recovered")
                        notify("HTTP OK")
                        h.enable_notify()
                        HTTP_FAILED = False
                    last_ok = h.ok
                    h.error_reset()
                    wait_interval()
                else:
                    log.debug("wrong response")
                    try:
                        h.error()
                    except ErrorThresholdReached:
                        log.error("too many wrong remote responses")
                        if h.notify:
                            notify("HTTP Error - too many wrong remote responses")
                            h.still_notified()
                        HTTP_FAILED = True
                        h.reset_all()
                    if last_ok is False and h.ok is False:
                        log.debug("http service changed to false")
                        if h.notify:
                            notify("HTTP Error")
                            h.still_notified()
                        HTTP_FAILED = True
                        h.reset_all()
                    last_ok = False
                    wait_interval()
            except BaseException as e:
                h.reset_all()
                log.error(e)
                HTTP_FAILED = True
                wait_interval()


class StatusHTTPServer(BaseHTTPRequestHandler):
    """
    class to create a simple webserver
    """
    def do_GET(self):
        """
        handler to manage get requests
        :return:
        """
        self.send_response(200)
        self.end_headers()
        try:
            response = write_http_response()
        except NameError:
            response = b"please wait"
        self.wfile.write(response)


def start_threads():
    """
    Start all threads used on this project.
    :return:
    """
    t = Tests()
    t1 = threading.Thread(target=t.test_http)
    t2 = threading.Thread(target=t.test_tcp)
    t1.start()
    t2.start()

    h = HTTPServer(('0.0.0.0', 8080), StatusHTTPServer, False)
    h.server_bind()
    h.server_activate()

    def serve_forever(h):
        with h:
            h.serve_forever()

    t3 = threading.Thread(target=serve_forever, args=(h,))
    t3.setDaemon(True)
    t3.start()
    t1.join()
    t2.join()


# logger format
log = logging.getLogger(__name__)
log_format = '%(asctime)s - [%(levelname)s] [%(threadName)s] [%(funcName)s:%(lineno)d]- %(message)s'

log_config = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "fatal": logging.FATAL
}

try:
    CONFIG = read_config()
except BaseException as err:
    log.error(err)
    sys.exit(1)

try:
    logging.basicConfig(level=log_config[CONFIG["LOG_LEVEL"].lower()], format=log_format)
except KeyError:
    logging.basicConfig(level=logging.CRITICAL, format=log_format)

if __name__ == '__main__':
    start_threads()
