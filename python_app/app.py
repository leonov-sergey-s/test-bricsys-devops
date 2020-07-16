from flask import Flask
from flask import render_template

import warnings
import pymysql
from pymysql.err import IntegrityError
from contextlib import closing
import os
import logging

import pandas as pd
import matplotlib.pyplot as plt

import sqlalchemy

MYSQL_DATABASE_HOST=os.getenv('MYSQL_DATABASE_HOST', 'localhost')
MYSQL_DATABASE_DB=os.getenv('MYSQL_DATABASE_DB', 'testBricsysDevOps')
MYSQL_DATABASE_USER=os.getenv('MYSQL_DATABASE_USER', 'testBricsysDevOps')
MYSQL_DATABASE_PASSWORD=os.getenv('MYSQL_DATABASE_PASSWORD', 'testSecurePassword')
MYSQL_DATABASE_PORT=3306
LIMIT_SLOWDOWN_OR_SPEEDUP=int(os.getenv('LIMIT_SLOWDOWN_OR_SPEEDUP', '30'))


connection = pymysql.connect(
    host=MYSQL_DATABASE_HOST,
    db=MYSQL_DATABASE_DB,
    user=MYSQL_DATABASE_USER,
    password=MYSQL_DATABASE_PASSWORD,
    charset='utf8mb4',
    local_infile=1,
    cursorclass=pymysql.cursors.DictCursor
)
warnings.filterwarnings('ignore', category=pymysql.Warning)
logging.basicConfig(level = logging.INFO)


sqlalchemyEngine = sqlalchemy.create_engine('mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4'.format(MYSQL_DATABASE_USER, MYSQL_DATABASE_PASSWORD, MYSQL_DATABASE_HOST, MYSQL_DATABASE_PORT, MYSQL_DATABASE_DB))

app = Flask(__name__)

def mysqlInitDbScheme():
    logging.info('Init database scheme')
    with connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS `testresults`");
        cursor.execute("CREATE TABLE `testresults` (`reportId` varchar(50), `buildid` int, `target` varchar(30), `name` varchar(50), `status` varchar(10), `duration` decimal(8,4), `physmemory` smallint, `virtmemory` smallint, `create_time` varchar(30), `testnode` varchar(30), INDEX (`reportId`), INDEX (`buildid`))")
        cursor.execute("DROP TABLE IF EXISTS `testresults_points`");

        cursor.execute("CREATE TABLE `testresults_points` (`testid` varchar(50) not null, `buildid` int, `slowdownOrSpeedup` decimal(8,2),  PRIMARY KEY(`testid`))")
        connection.commit()

def mysqlLoadDataInFile(fileName):
    logging.info('Loading data from {}'.format(fileName))
    with connection.cursor() as cursor:
        cursor.execute("DROP TEMPORARY TABLE IF EXISTS `_reportn`")
        cursor.execute("CREATE TEMPORARY TABLE `_reportn` (`buildid` int, `target` varchar(30), `name` varchar(50), `status` varchar(10), `duration` varchar(250), `physmemory` smallint, `virtmemory` smallint, `create_time` varchar(30), `testnode` varchar(30))")
        cursor.execute("LOAD DATA LOCAL INFILE %s INTO TABLE `_reportn` FIELDS TERMINATED BY '\\t' LINES TERMINATED BY '\\n' IGNORE 2 LINES", "/opt/app/txt_files/normalized/" + fileName)
        cursor.execute("INSERT INTO testresults SELECT %s testid, buildid, target, name, status, CAST(REPLACE(duration, ',', '.') as decimal(8,4)) duration, physmemory, virtmemory, create_time, testnode from `_reportn`", fileName)
        cursor.execute("DROP TEMPORARY TABLE `_reportn`")
        connection.commit()

def mysqlInsertResultPoints(pointsList):
    with connection.cursor() as cursor:
        query = "INSERT INTO `testresults_points` VALUES "
        values = []
        for item in pointsList: values.append((f"{item['point']['reportId']} - {item['point']['buildid']}", item['point']['buildid'], item['slowdownOrSpeedup']))
        query += ', '.join(connection.escape(v) for v in values)
        cursor.execute(query)
        connection.commit()

def saveRepotPlotImage(reportId, df):
    ax = df.plot(x='create_time', y='duration', figsize=(10,4))
    ax.set_xlabel("Build create time")
    ax.set_ylabel("Duration")
    plt.savefig("static/images/{}.png".format(reportId))

def calcSlowdownOrSpeedup(duration, prevDuration):
    if (prevDuration == duration): slowdownOrSpeedup = 0
    elif (prevDuration == 0): slowdownOrSpeedup = 100
    else: slowdownOrSpeedup = 100 - (duration/prevDuration * 100)
    return slowdownOrSpeedup

def findPoints(reportId):
    logging.info('{}: Calculate slowdown or speed up points (limit {}%)'.format(reportId, LIMIT_SLOWDOWN_OR_SPEEDUP))
    sql = "SELECT * FROM testresults WHERE reportId='{}' and status='success' ORDER BY buildid desc".format(reportId)

    df = pd.read_sql_query(sql, sqlalchemyEngine, parse_dates=['create_time'])
    saveRepotPlotImage(reportId, df)
    df.insert(loc=6, column='duration_ewm', value=df['duration'].ewm(alpha=0.8).mean())

    prev = {'duration_ewm': 0}
    result = []
    for index, row in df.iterrows():
        slowdownOrSpeedup = calcSlowdownOrSpeedup(row['duration_ewm'], prev['duration_ewm'])
        if (index != 0 and abs(slowdownOrSpeedup) >= LIMIT_SLOWDOWN_OR_SPEEDUP): 
            result.append({'point': row, 'prev': prev, 'slowdownOrSpeedup':  calcSlowdownOrSpeedup(row['duration'], prev['duration'])})
        prev = row

    return result



testresults_points = []

def processingTxtFiles():
    global testresults_points
    for root, dirs, files in os.walk('/opt/app/txt_files/normalized'):
        for fileName in sorted(files):            
            if fileName.endswith('.txt'): 
                mysqlLoadDataInFile(fileName)
                pointsList = findPoints(fileName)
                if (len(pointsList) != 0):
                    mysqlInsertResultPoints(pointsList)
                    testresults_points.append(pointsList)

@app.route('/')
def showRootHtmlPage():
    global testresults_points
    return render_template('points.html', results=testresults_points, limitSlowdownOrSpeedup=LIMIT_SLOWDOWN_OR_SPEEDUP)

mysqlInitDbScheme()
processingTxtFiles()

connection.close()
sqlalchemyEngine.dispose()

if __name__ == '__main__':
    app.run(debug=False,use_reloader=False,host='0.0.0.0',port=5000)
