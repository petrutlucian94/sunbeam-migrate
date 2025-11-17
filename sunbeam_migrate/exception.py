# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0


class SunbeamMigrateException(Exception):
    msg_fmt = "An exception has been encountered."

    def __init__(self, message=None, **kwargs):
        if not message:
            message = self.msg_fmt % kwargs
        super(SunbeamMigrateException, self).__init__(message)


class Invalid(SunbeamMigrateException):
    msg_fmt = "Invalid data."


class InvalidInput(Invalid):
    msg_fmt = "Invalid input provided."


class NotFound(SunbeamMigrateException):
    msg_fmt = "Resource not found."
