class FTPReply:


    READY="220 Hybrid FTP Server Ready\r\n"


    LOGIN_REQUIRED = (
        "530 Not logged in\r\n"
    )


    LOGIN_OK = (
        "230 Login successful\r\n"
    )


    USER_OK = (
        "331 Username OK\r\n"
    )


    QUIT = (
        "221 Goodbye\r\n"
    )


    NOT_IMPLEMENTED = (
        "502 Command not implemented\r\n"
    )


    TRANSFER_START = (
        "150 Opening data connection\r\n"
    )


    TRANSFER_OK = (
        "226 Transfer complete\r\n"
    )