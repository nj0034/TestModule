from datetime import datetime


def convert_datetime(datetime_, origin='%Y.%m.%d %H:%M:%S', dest='%Y-%m-%d %H:%M:%S'):
    datetime_ = datetime.strptime(datetime_, origin)
    return datetime_.strftime(dest)
