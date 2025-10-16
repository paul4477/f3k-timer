import asyncio
import json
import time
import logging
import os
from aiohttp import web, ClientConnectionError
from aiohttp_sse import sse_response
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
        self.client_queues = set()
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
                web.get("/state-stream", self.handle_state_stream),

                web.get("/reset", self.handle_reset),
                web.post("/timesync/", self.handle_timesync),
                #web.get("/ws/", self.ws_handler),
                web.post("/load_event", self.handle_load_event),

                web.get("/groupData", self.handle_groupData),
                web.get("/roundData", self.handle_roundData),
            ]
        )

    async def handle_state_stream(self, request):
        # Serve the SSE stream 
        
        queue = asyncio.Queue()
        self.client_queues.add(queue)
        self.logger.debug(f"New state-stream, {request.remote}, {len(self.client_queues)} queues, id(queue): {id(queue)}")     
        async with sse_response(request) as resp:
            while resp.is_connected():
                self.logger.debug(f"{request.remote} is connected.")     
                q_item = await queue.get()
                if len(q_item)==2:
                    payload, etype = q_item
                elif len(q_item)==1:
                    payload, etype = q_item[0], None
                self.logger.debug(f"id(queue): {id(queue)} yielded event ({etype}).")     
                try:
                    await resp.send(payload, event=etype)
                except ClientConnectionError:
                    self.logger.debug(f"Closing state-stream, {request.remote}, ClientConnectionError")     
                    break
        self.client_queues.remove(queue)
        self.logger.debug(f"Closing state-stream, {request.remote}, {len(self.client_queues)} queues, id(queue): {id(queue)}")     
        return resp   


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
        if ((not self.limit_rate(state)) and state and state.round):
            d = state.get_dict()
            for q in list(self.client_queues):
                try: 
                    await q.put_nowait((json.dumps(d), "time"))
                except: 
                    pass

    async def onSecond(self, state):
        # Not needed since we're updating onTick
        pass

    async def onNewSection(self, state):
        # Section info is included in time updates
        if ((not self.limit_rate(state)) and state and state.round):
            for q in list(self.client_queues):
                q.put_nowait((json.dumps({'type': state.section.__class__.__name__}), "sectionData"))

    async def onNewGroup(self, state):
        if ((not self.limit_rate(state)) and state and state.round):
            d = { 'pilots':[] }
            for pid in state.group.pilots:
                d['pilots'].append(state.player.pilots[pid].name)

            d['group_number'] = state.group.group_number
            d['group_letter'] = state.group.group_letter
            
            self.groupDict = d
            js = json.dumps(d)
            assert len(js)<250, f"Group data too large: {len(js)}"
            for q in list(self.client_queues):
                q.put_nowait((js, "groupData"))

    async def onNewRound(self, state):
        if ((not self.limit_rate(state)) and state and state.round):
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
            js = json.dumps(d)
            assert len(js)<250, f"Round data too large: {len(js)}"
            for q in list(self.client_queues):
                q.put_nowait((js, "roundData"))
