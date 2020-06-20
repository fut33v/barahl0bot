import pymysql
from database import Barahl0botDatabase
import re


if __name__ == "__main__":
    _DATABASE = Barahl0botDatabase('barahlochannel')

    connection = _DATABASE.get_connection()
    with connection.cursor() as cur:
        sql = "select descr from {t} where descr is not null " \
              "union " \
              "select comments from {t} where comments is not null;".format(t=_DATABASE._goods_table)

        cur.execute(sql)
        descr_comments = cur.fetchall()

    words_dictionary = {}

    for dc in descr_comments:
        for x in dc:
            #words = x.split(' ')
            words = re.split('; |, |\*|\n|\.| ', x)
            for w in words:
                if len(w) < 4:
                    continue
                if w not in words_dictionary:
                    words_dictionary[w] = 1
                else:
                    words_dictionary[w] += 1
            # print(words)

    # print(words_dictionary)
    for k in sorted(words_dictionary, key=words_dictionary.get, reverse=True):
        print(k, words_dictionary[k])


