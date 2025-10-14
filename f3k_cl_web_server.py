import asyncio
import json
import time
import logging
import os
from aiohttp import web
from plugin_base import PluginBase

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*"
}

class WebFrontend(PluginBase):
    def __init__(self, events, config):
        super().__init__(events, config)
        self.port = config.get('port', 8080)
        self.runner = None
        self.app = web.Application()
        self.ticks = 0
        self.clients = set()
        self.events = events
        self.event_data_loaded = False
        self.logger = logging.getLogger(self.__class__.__name__)
        self.last_update = 0
        self.groupDict = {}
        self.roundDict = {}
        #self.register_more_handlers()
        # Add route for default page
        
        self.app.add_routes(
            [
                web.static("/assets/", os.path.join(os.path.dirname(__file__), "assets")),
                web.get("/", self.handle_default_page),
                
                web.get("/run", self.handle_run_page),
                web.get("/view", self.handle_view_page),
                web.post("/control/{command}", self.handle_control),

                web.get("/reset", self.handle_reset),
                web.post("/timesync/", self.handle_timesync),
                web.get("/ws/", self.ws_handler),
                web.post("/load_event", self.handle_load_event),

                web.get("/groupData", self.handle_groupData),
                web.get("/roundData", self.handle_roundData),
            ]
        )

    async def handle_groupData(self, request):
        # Serve the json data
        body =json.dumps(self.groupDict)
        return web.Response(
            content_type="application/json", body=body,
        )    
     


    async def handle_roundData(self, request):
        # Serve the json data
        body =json.dumps(self.roundDict)
        return web.Response(
            content_type="application/json", body=body,
        )    

    async def handle_reset(self, request):
        # Serve the static HTML file
        self.logger.info(f"Resetting event data, {self.event_data_loaded}")
        if self.event_data_loaded: self.event_data_loaded = False
        self.events.trigger(f"player.stop")
        
        raise web.HTTPFound('/')




    async def handle_default_page(self, request):
        self.logger.info(f"Serving default, {self.event_data_loaded}")
        # Serve the static HTML file
        if self.event_data_loaded:
            file_path = os.path.join(os.path.dirname(__file__), "assets", "html", "event_runner.html")
        else:
            file_path = os.path.join(os.path.dirname(__file__), "assets", "html", "event_selector.html")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return web.Response(text=content, content_type="text/html")
        except FileNotFoundError:
            return web.Response(status=404, text="Default page not found")

    async def handle_run_page(self, request):
        self.logger.info(f"Serving run, {self.event_data_loaded}")
        if self.event_data_loaded:# Serve the static HTML file
            file_path = os.path.join(os.path.dirname(__file__), "assets", "html", "event_runner.html")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return web.Response(text=content, content_type="text/html")
            except FileNotFoundError:
                return web.Response(status=404, text="Run page not found")
        else:
            raise web.HTTPFound('/')

    async def handle_view_page(self, request):
        self.logger.info(f"Serving run, {self.event_data_loaded}")
        if self.event_data_loaded:# Serve the static HTML file
            file_path = os.path.join(os.path.dirname(__file__), "assets", "html", "event_viewer.html")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return web.Response(text=content, content_type="text/html")
            except FileNotFoundError:
                return web.Response(status=404, text="Run page not found")
        else:
            raise web.HTTPFound('/')

    # json reponse for time sync requests from web clients
    async def handle_timesync(self, request):
        data = await request.json()
        try: id = data['id']
        except: id = "null"
        body=json.dumps({"jsonrpc": "2.0", "result": time.time()*1000, "id": f"{id}" })
        return web.Response(
            content_type="application/json", body=body,
        )

    # json reponse for time sync requests from web clients
    async def handle_load_event(self, request):
        self.logger.debug("in handle_load_event")
        data = await request.json()
        self.logger.debug(f"Length of data received: {len(data)}")
        for k in data.keys():
            self.logger.debug(f"  {k}: {data[k]}")
        try:
            
            self.logger.info(f"Handling load_event {data['event']['event_id']}:{data['event']['event_name']}")
            self.events.trigger(f"player.data_available", data)
            self.event_data_loaded = True  
            ## Do some stuff with the data 
        except KeyError:
            return web.Response(status=400, text="Missing 'event' in request")
        else:
            #return web.Response(status=200, text=f"Event load requested")
            raise web.HTTPFound('/run')

    async def handle_control(self, request):
        self.events.trigger(f"player.{request.match_info['command']}")
        return web.Response(status=200, text=f"Done")

    ## Handle control commands from web client(s) - pause, skip, reset etc
    async def ws_handler(self, request):
        self.logger.debug("in ws_handler")
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws) # Add client to list of connected clients
        self.logger.info (f"Client connected: {request.remote} Total: {len(self.clients)}")
        try:
          async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                if msg.data == 'close':
                  await ws.close()
                else:
                  self.logger.debug(f"Message from client: {msg.data}")
                  # Handle control commands from web client(s) - pause, skip, reset etc

                  try:
                      data = json.loads(msg.data)
                      command = data.get("command")
                  except Exception as e:
                      self.logger.error(f"Failed to parse message: {msg.data} ({e})")
                      continue

                  match command:
                      case "start":
                          self.logger.info("Received start command")
                          self.events.trigger(f"player.start")
                      case "pause":
                          self.logger.info("Received pause command")
                          self.events.trigger(f"player.pause")
                      case "skip_fwd":
                          self.logger.info("Received skip_fwd command")
                          self.events.trigger(f"player.skip_fwd", 15)  # skip forward 15 seconds
                      case "skip_back":
                          self.logger.info("Received skip_back command")
                          self.events.trigger(f"player.skip_back", 15)  # skip back 15 seconds
                      case "skip_previous":
                          self.logger.info("Received skip_previous command")
                          self.events.trigger(f"player.skip_previous")
                      case "skip_next":
                          self.logger.info("Received skip_next command")
                          self.events.trigger(f"player.skip_next")
                      case "goto":
                          self.logger.info("Received goto command")
                          try:
                              r = int(data.get("round", 0))
                              g = int(data.get("group", 0))
                          except ValueError:
                              self.logger.error(f"Bad data for goto: round: {data.get('round', 0)}, group: {data.get('group',0)}")
                          self.events.trigger(f"player.goto", r, g)
                      case "quit":
                          self.logger.info("Received quit command")
                          self.events.trigger(f"player.quit")

                      case _:
                          self.logger.warning(f"Unknown command: {command}")

            elif msg.type == web.WSMsgType.ERROR:
                self.logger.info(f"WebSocket connection closed with exception {ws.exception()}")
        finally:
          self.clients.remove(ws)
          self.logger.info(f"Client disconnected. Total: {len(self.clients)}")
        return ws
    

    
    async def startup(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", self.port)
        await site.start()
 
    async def shutdown(self):
        if self.runner:
            await self.runner.cleanup()
    
    def limit_rate(self, state):
        ## Check how recently we've been called
        ## Reduce rate of updates to max 6 per second
        try:
            if state.section.get_serial_code()=="LT": ## Announcement
                return False
        except AttributeError:
            pass
        now = time.time()
        if (now - self.last_update) >= 1/6:
            self.last_update = now
            return False
        else:
            return True

    async def onTick(self, state):
        # Send the bits of state needed to the web clients
        #self.logger.debug(f"Sending update to web client.Limit rate?: {self.limit_rate(state)} {state.section.__class__.__name__} {state.round}")
        if ((not self.limit_rate(state)) and state and state.round):
            d = state.get_dict()
            #self.logger.debug(f"Sending to client: {d}")

            msg = json.dumps({"type": "time", "data": d} )
            for ws in list(self.clients):
                #self.logger.debug(f"Sending to client: {msg}")
                try: 
                    await ws.send_str(msg)
                except: #ConnectionResetError ??
                    pass

    async def onSecond(self, state):
        pass
    async def onNewSection(self, state):
        #if self.enabled():
        pass
    async def onNewGroup(self, state):
        d = {'pilots':[]}
        for pid in state.group.pilots:
            d['pilots'].append(state.player.pilots[pid].name)
        d['group_number'] = state.group.group_number
        d['group_letter'] = state.group.group_letter
        self.groupDict = d
        msg = json.dumps({"type": "groupData", "data": d} )
        for ws in list(self.clients):
            #self.logger.debug(f"Sending to client: {msg}")
            try: 
                await ws.send_str(msg)
            except: #ConnectionResetError ??
                pass        
        

    async def onNewRound(self, state):
        d = {}
        d['round_number'] = state.round.round_number
        d['group_count'] = len(state.round.groups)
        d['window_time'] = state.round.windowTime
        d['task'] = {
        'short_code': state.round.short_code,
        'short_name': state.round.short_name,
        'name': state.round.task_name,
        'description': state.round.task_description,
        }
        self.roundDict = d
        msg = json.dumps({"type": "roundData", "data": d} )
        for ws in list(self.clients):
            #self.logger.debug(f"Sending to client: {msg}")
            try: 
                await ws.send_str(msg)
            except: #ConnectionResetError ??
                pass        
        await self.onNewGroup(state)
