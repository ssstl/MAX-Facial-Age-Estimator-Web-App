import sqlite3 as lite

#存储型XSS是指数据通过不可信的数据源（数据库、文件等）进入WEB程序中，WEB程序没有验证该数据就将其传送给了用户。这些数据可能包含恶意代码，被用户的浏览器执行，造成跨站脚本攻击。
def selectVer(master_db):
    con = lite.connect(master_db)
    cur = con.cursor()
    cur.execute('SELECT SQLITE_VERSION()')
    data = cur.fetchone()
    print ("SQLite version: %s" % data)
