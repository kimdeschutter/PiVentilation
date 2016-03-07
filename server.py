#!/usr/bin/env python
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import Adafruit_DHT
import time
import RPi.GPIO as GPIO
import sqlite3
import os
import json
import math

GPIO.setmode(GPIO.BOARD)
GPIO.setup(29, GPIO.OUT)
GPIO.setup(33, GPIO.OUT)
GPIO.output(29,True)
GPIO.output(33,True)

modus = "2"
status = 0
temp1 = 0
temp2 = 0
humidity1 = 0
humidity2 = 0
pathname = os.path.dirname(os.path.abspath(__file__))
dbpath = pathname + "/log.db"

try:
	wss =[]
	class WSHandler(tornado.websocket.WebSocketHandler):
		def open(self):
			global modus, status, temp1, temp2, humidity1, humidity2
			print("New user is connected.\n") 
			if self not in wss:
				wss.append(self)
			self.write_message(str(temp1) + ";" + str(humidity1) + ";" + str(temp2) + ";" + str(humidity2) + ";" + str(modus) + ";" + str(status))
		def on_message(self, message):
			global modus, status, temp1, temp2, humidity1, humidity2
			if message != None:
				modus = message
				if modus == "1" and status == 0:
					GPIO.output(29,False)
					GPIO.output(33,False)
					status = 1
					LogVentilator(status, modus)
				if modus == "0" and status == 1:
					GPIO.output(29,True)
					GPIO.output(33,True)
					status = 0
					LogVentilator(status, modus)
			self.write_message(str(temp1) + ";" + str(humidity1) + ";" + str(temp2) + ";" + str(humidity2) + ";" + str(modus) + ";" + str(status))
		def on_close(self):
			print("connection closed\n")
			if self in wss:
				wss.remove(self)

	class GrapHandler(tornado.websocket.WebSocketHandler):
		def open(self):
			conn=sqlite3.connect(dbpath)
               		curs=conn.cursor()
               		curs.execute("SELECT datetime((strftime('%s', timestamp) / 300) * 300, 'unixepoch') interval, round(avg(humidity1),1) \
					, round(avg(humidity2),1), round(avg(temp1),1), round(avg(temp2),1) from sensor GROUP BY interval ORDER BY timestamp DESC LIMIT 120")
					#curs.execute("SELECT timestamp, humidity1, humidity2 FROM sensor ORDER BY timestamp DESC  LIMIT 144")
			webdata = json.dumps(curs.fetchall())

			conn.close()
			self.write_message(webdata)

	class IndexPageHandler(tornado.web.RequestHandler):
		def get(self):
			self.render("index.html")

	application = tornado.web.Application([
		(r'/', IndexPageHandler),
		(r'/ws', WSHandler),
		(r'/graph', GrapHandler),
		(r'/javascript/(.*)',tornado.web.StaticFileHandler, {'path': '/home/pi/PiVentilation/javascript'},),
		(r'/static/(.*)', tornado.web.StaticFileHandler, {'path': '/home/pi/PiVentilation/static'}),
	],)

	if __name__ == "__main__":
	  interval_msec = 20000

	  def wsSend(message):
		for ws in wss:
		  if not ws.ws_connection.stream.socket:
			print("Web socket does not exist anymore!!!")
			wss.remove(ws)
		  else:
			ws.write_message(message)

	  def read_temp():
		global modus, status, temp1, temp2, humidity1, humidity2
		DHT_TYPE = Adafruit_DHT.DHT22
		DHT1_PIN = 4
		DHT2_PIN = 17
		humidity1, temp1 = dht22(DHT_TYPE, DHT1_PIN)
		humidity2, temp2 = dht22(DHT_TYPE, DHT2_PIN)

		rh1 = humidity1*math.exp(temp1*10*0.006235398)/math.exp(21*10*0.006235398)
		rh2 = humidity2*math.exp(temp2*10*0.006235398)/math.exp(21*10*0.006235398)

		if modus == "2" and status == 0 and (rh1 > 65 or rh2 > 65):
			GPIO.output(29,False)
			GPIO.output(33,False)
			status = 1
			LogVentilator(status, modus)
		if modus == "2" and status == 1 and rh1 <= 59 and rh2 <= 59:
			GPIO.output(29,True)
			GPIO.output(33,True)
			status = 0
			LogVentilator(status, modus)
		
		wsSend(str(temp1) + ";" + str(humidity1) + ";" + str(temp2) + ";" + str(humidity2) + ";" + str(modus) + ";" + str(status))
		conn=sqlite3.connect(dbpath)
		curs=conn.cursor()
		curs.execute("INSERT INTO sensor(temp1, humidity1, temp2, humidity2) VALUES(?,?,?,?)", (temp1, humidity1, temp2, humidity2))
		conn.commit()
		conn.close()

	  def dht22(DHT_TYPE, DHT_PIN):
		humidity, temp =  Adafruit_DHT.read(DHT_TYPE, DHT_PIN)
		while (humidity == None):
			time.sleep(3)
			humidity, temp =  Adafruit_DHT.read(DHT_TYPE, DHT_PIN)
		return (round(humidity,1), round(temp,1))

	  def LogVentilator(status, modus):
		conn=sqlite3.connect(dbpath)
		curs=conn.cursor()
		curs.execute("INSERT INTO ventilator(status, modus) VALUES(?,?)", (status, modus))
		conn.commit()
		conn.close()
	  
	  http_server = tornado.httpserver.HTTPServer(application)
	  http_server.listen(8888)
		
	  main_loop = tornado.ioloop.IOLoop.instance()
	  sched_temp = tornado.ioloop.PeriodicCallback(read_temp, interval_msec, io_loop = main_loop)

	  sched_temp.start()
	  main_loop.start()
except:
	print("\nexiting")
	GPIO.cleanup()
