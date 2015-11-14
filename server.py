#!/usr/bin/env python
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import Adafruit_DHT
import time
import RPi.GPIO as GPIO
import sqlite3

status = 0
temp1 = 0
temp2 = 0
humidity1 = 0
humidity2 = 0

try:
	wss =[]
	class WSHandler(tornado.websocket.WebSocketHandler):
		def open(self):
			global status, temp1, temp2, humidity1, humidity2
			print("New user is connected.\n") 
			if self not in wss:
				wss.append(self)
			self.write_message(str(temp1) + ";" + str(humidity1) + ";" + str(temp2) + ";" + str(humidity2) + ";" + str(status))
		def on_message(self, message):
			global status, temp1, temp2, humidity1, humidity2
			if message != None:
				status = message
			# if message == "toggle":
				# if status == 1:
					# status = 0
					# print("uit")
					# #GPIO.output(7,True)
				# else:
					# status = 1
					# print("aan")
					# #GPIO.output(7,False)
			#print(str(temp1) + ";" + str(humidity1) + ";" + str(temp2) + ";" + str(humidity2) + ";" + str(status))
			self.write_message(str(temp1) + ";" + str(humidity1) + ";" + str(temp2) + ";" + str(humidity2) + ";" + str(status))
		def on_close(self):
			print("connection closed\n")
			if self in wss:
				wss.remove(self)

	class IndexPageHandler(tornado.web.RequestHandler):
		def get(self):
			self.render("index2.html")

	application = tornado.web.Application([
		(r'/', IndexPageHandler),
		(r'/ws', WSHandler),
		(r'/graph', GrapHandler),
		(r'/javascript/(.*)',tornado.web.StaticFileHandler, {'path': '/home/pi/control/javascript'},),
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
		global status, temp1, temp2, humidity1, humidity2
		DHT_TYPE = Adafruit_DHT.DHT22
		DHT1_PIN = 4
		DHT2_PIN = 17
		humidity1, temp1 = dht22(DHT_TYPE, DHT1_PIN)
		humidity2, temp2 = dht22(DHT_TYPE, DHT2_PIN)

		#print(str(temp1) + ";" + str(humidity1) + ";" + str(temp2) + ";" + str(humidity2) + ";" + str(status))
		wsSend(str(temp1) + ";" + str(humidity1) + ";" + str(temp2) + ";" + str(humidity2) + ";" + str(status))
		conn=sqlite3.connect('/home/pi/control/log.db')
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

	  http_server = tornado.httpserver.HTTPServer(application)
	  http_server.listen(8888)
		
	  main_loop = tornado.ioloop.IOLoop.instance()
	  sched_temp = tornado.ioloop.PeriodicCallback(read_temp, interval_msec, io_loop = main_loop)

	  sched_temp.start()
	  main_loop.start()
except:
	print("\nexiting")
	#GPIO.cleanup()
