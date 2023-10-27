import gevent
import logging
import time
import requests  # Use synchronous requests library

from .const import (ACCEPT_ENCODING, ACCEPT_HEADER, ALL, DEFAULT_TIMEOUT_TIME, BUSY,
                    EPSON_KEY_COMMANDS, HTTP_OK, INV_SOURCES, SOURCE,
                    TIMEOUT_TIMES, TURN_OFF, TURN_ON)

_LOGGER = logging.getLogger(__name__)

class Projector:
    def __init__(self, host, port=80, encryption=False):
        self._host = host
        self._port = port
        self._encryption = encryption
        http_proto = 'https' if self._encryption else 'http'
        self._http_url = '{http_proto}://{host}:{port}/cgi-bin/'.format(
            http_proto=http_proto,
            host=self._host,
            port=self._port)
        referer = "{http_proto}://{host}:{port}/cgi-bin/webconf".format(
            http_proto=http_proto,
            host=self._host,
            port=self._port)
        self._headers = {
            "Accept-Encoding": ACCEPT_ENCODING,
            "Accept": ACCEPT_HEADER,
            "Referer": referer
        }
        self.__initLock()

    def __initLock(self):
        self._isLocked = False
        self._timer = 0
        self._operation = False

    def __setLock(self, command):
        if command in (TURN_ON, TURN_OFF):
            self._operation = command
        elif command in INV_SOURCES:
            self._operation = SOURCE
        else:
            self._operation = ALL
        self._isLocked = True
        self._timer = time.time()

    def __unLock(self):
        self._operation = False
        self._timer = 0
        self._isLocked = False

    def __checkLock(self):
        if self._isLocked:
            if (time.time() - self._timer) > TIMEOUT_TIMES[self._operation]:
                self.__unLock()
                return False
            return True
        return False

    def get_property(self, command):
        _LOGGER.debug("Getting property %s", command)
        if self.__checkLock():
            return BUSY
        timeout = self.__get_timeout(command)
        response = self.send_request(
            timeout=timeout,
            params=EPSON_KEY_COMMANDS[command],
            type='json_query')
        if not response:
            return False
        try:
            return response['projector']['feature']['reply']
        except KeyError:
            return BUSY

    def send_command(self, command):
        _LOGGER.debug("Sending command to projector %s", command)
        if self.__checkLock():
            return False
        self.__setLock(command)
        response = self.send_request(
            timeout=self.__get_timeout(command),
            params=EPSON_KEY_COMMANDS[command],
            type='directsend',
            command=command)
        return response

    def send_request(self, params, timeout, type='json_query', command=False):
        try:
            url = '{url}{type}'.format(
                url=self._http_url,
                type=type)
            response = requests.get(url, params=params, headers=self._headers, timeout=timeout)
            if response.status_code != HTTP_OK:
                _LOGGER.warning("Error message %d from Epson.", response.status_code)
                return False
            if command == TURN_ON and self._powering_on:
                self._powering_on = False
            if type == 'json_query':
                return response.json()
            return response
        except requests.exceptions.RequestException:
            _LOGGER.error("Error request")
            return False

    def __get_timeout(self, command):
        if command in TIMEOUT_TIMES:
            return TIMEOUT_TIMES[command]
        else:
            return DEFAULT_TIMEOUT_TIME
