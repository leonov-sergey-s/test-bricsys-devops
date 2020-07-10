from flask import Flask
from flask import render_template

import warnings
import pymysql
from pymysql.err import IntegrityError
from contextlib import closing
import os
import logging

connection = pymysql.connect(
    host=os.getenv('MYSQL_DATABASE_HOST', 'localhost'),
    db=os.getenv('MYSQL_DATABASE_DB', 'mytestdatabase'),
    user=os.getenv('MYSQL_DATABASE_USER', 'root'),
    password=os.getenv('MYSQL_DATABASE_PASSWORD', 'password'),
    charset='utf8mb4',
    local_infile=1,
    cursorclass=pymysql.cursors.DictCursor
)
warnings.filterwarnings('ignore', category=pymysql.Warning)
logging.basicConfig(level = logging.INFO)

app = Flask(__name__)

def mysqlInitDbScheme():
    logging.info('Init database scheme')
    with connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS `testresults`");
        cursor.execute("CREATE TABLE `testresults` (`testid` varchar(50), `buildid` int, `target` varchar(30), `name` varchar(50), `status` varchar(10), `duration` decimal(8,4), `physmemory` smallint, `virtmemory` smallint, `create_time` varchar(30), `testnode` varchar(30), INDEX (`testid`))")
        cursor.execute("DROP TABLE IF EXISTS `testresults_points`");
        cursor.execute("CREATE TABLE `testresults_points` (`testid` varchar(50) not null, `buildid` int, `slowdownOrSpeedup` decimal(8,2), `prevTestId` varchar(50) not null, PRIMARY KEY(`testid`), INDEX (`prevTestId`), INDEX (`buildid`))")
        connection.commit()

def mysqlLoadDataInFile(fileName):
    buildidPrefix = fileName + " - "
    logging.info('Loading data from {}'.format(fileName))
    with connection.cursor() as cursor:
        cursor.execute("DROP TEMPORARY TABLE IF EXISTS `_reportn`")
        cursor.execute("CREATE TEMPORARY TABLE `_reportn` (`buildid` int, `target` varchar(30), `name` varchar(50), `status` varchar(10), `duration` varchar(250), `physmemory` smallint, `virtmemory` smallint, `create_time` varchar(30), `testnode` varchar(30))")
        cursor.execute("LOAD DATA LOCAL INFILE %s INTO TABLE `_reportn` FIELDS TERMINATED BY '\\t' LINES TERMINATED BY '\\n' IGNORE 2 LINES", "/opt/app/txt_files/normalized/" + fileName)
        cursor.execute("INSERT INTO testresults SELECT CONCAT(%s, buildid) testid, buildid, target, name, status, CAST(REPLACE(duration, ',', '.') as decimal(8,4)) duration, physmemory, virtmemory, create_time, testnode from `_reportn`", buildidPrefix)
        cursor.execute("DROP TEMPORARY TABLE `_reportn`")
        connection.commit()

def loadDataToMysql():
    for root, dirs, files in os.walk('/opt/app/txt_files/normalized'):
        for file in sorted(files):            
            if file.endswith('.txt'): 
                mysqlLoadDataInFile(file)


def mysqlInsertPointWithoutCommit(testId, buildId, slowdownOrSpeedup, prevTestId):
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO `testresults_points` VALUES (%s, %s, %s, %s)", (testId, buildId, slowdownOrSpeedup, prevTestId))       

def findPoints():
    limitSlowdownOrSpeedup = 80
    logging.info('Calculate slowdown or speed up points (limit {}%)'.format(limitSlowdownOrSpeedup))
    with connection.cursor() as cursor:
        cursor.execute("SELECT `testid`, `buildid`, `duration`, `status`  FROM `testresults` ORDER BY buildid, testid DESC")
    with cursor as pointer:
        prevDuration = 0
        prevBuildId = '0000'
        prevTestId = '0000'
        index = 0
        for row in pointer:
            if (row['buildid'] == prevBuildId):
                if (prevDuration == row['duration']): slowdownOrSpeedup = 0
                elif (prevDuration == 0): slowdownOrSpeedup = 100
                else:
                    slowdownOrSpeedup = 100 - (row['duration']/prevDuration * 100)
                if (abs(slowdownOrSpeedup) >= limitSlowdownOrSpeedup): mysqlInsertPointWithoutCommit(row['testid'], row['buildid'], slowdownOrSpeedup, prevTestId)
                index += 1
            else:
                index = 0
            prevDuration = row['duration']
            prevBuildId = row['buildid']
            prevTestId = row['testid']
        connection.commit()    


@app.route('/')
def showRootHtmlPage():
    cursor = connection.cursor()
    cursor.execute("SELECT *, ct.name testName, ct.status testStatus, ct.duration testDuration, pt.status prevTestStatus, pt.duration prevTestDuration FROM testresults_points p INNER JOIN testresults ct on p.testid = ct.testid INNER JOIN testresults pt on p.prevTestId = pt.testid ORDER BY p.buildid DESC, p.testid")
    results = cursor.fetchall()
    cursor.close()
    return render_template('points.html', results=results)

mysqlInitDbScheme()
loadDataToMysql()
findPoints()

if __name__ == '__main__':
    app.run(debug=False,use_reloader=False,host='0.0.0.0',port=5000)

