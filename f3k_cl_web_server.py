import asyncio
from email.mime import audio
from email.mime import audio
import json
import time
import logging
import os
from aiohttp import web, ClientConnectionError
from aiohttp_sse import sse_response
import jinja2
import aiohttp_jinja2
import pygame
from plugin_base import PluginBase

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*"
}

class WebFrontend(PluginBase):
    def __init__(self, events, config, player=None):
        super().__init__(events, config)
        self.port = config.get('port', 8080)
        self.runner = None
        self.app = web.Application()
        self.player = player
        self.ticks = 0
        self.clients = set()
        self.client_queues = set()
        self.events = events
        self.event_data_loaded = False
        self.logger = logging.getLogger(self.__class__.__name__)
        self.groupDict = {}
        self.roundDict = {}
        #self.register_more_handlers()
        # Add route for default page
        
        self.app.add_routes(
            [
                web.static("/assets/", os.path.join(os.path.dirname(__file__), "assets")),
                web.get("/", self.handle_default_page),
                
                #web.get("/run", self.handle_run_page),
                #web.get("/view", self.handle_view_page),
                
                web.post("/control/{command}", self.handle_control),
                web.get("/goto/{round:[0-9]+}/{group:[0-9]+}", self.handle_goto),
                web.get("/state-stream", self.handle_state_stream),
                web.get("/test", self.test),

                #web.get("/reset", self.handle_reset),
                web.post("/timesync/", self.handle_timesync),
                web.post("/load_event", self.handle_load_event),
                web.post("/set_event_config", self.handle_set_event_config),

                web.get("/groupData", self.handle_groupData),
                web.get("/roundData", self.handle_roundData),

                web.get("/sound-test", self.handle_sound_test_page),
                web.post("/play-sound", self.handle_play_sound),
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


    async def handle_default_page_old(self, request):
        self.logger.info(f"Serving default, {self.event_data_loaded}")
        
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

    async def handle_default_page(self, request):
        self.logger.info(f"Serving run, {self.event_data_loaded}")
        if self.event_data_loaded:# Serve the event runner page
            template_path = "event_runner.html"
            rounds_options = ""
            groups_options = ""
            max_groups = 0
            for round in self.player.rounds:
               rounds_options += f'<option value="{round.round_number}">{round.round_number}: {round.short_name}</option>'
               max_groups = max(max_groups, round.group_count)
            for group in range(1, max_groups + 1):
               groups_options += f'<option value="{group}">{chr(64+group)}</option>'
            self.logger.debug(f"Round options HTML: {rounds_options}")
            self.logger.debug(f"Group options HTML: {groups_options}")
            event_config = self.player.event_config or {}
            context = {
                'rounds': rounds_options,
                'groups': groups_options,
                'prep_time': event_config.get('prep_time', 300),
                'group_separation_time': event_config.get('group_separation_time', 120),
                'use_strict_test_time': event_config.get('use_strict_test_time', False),
                'competition_start_time': event_config.get('competition_start_time', 600),
            }
            response = aiohttp_jinja2.render_template(template_path, request,
                                          context=context)
            return response
        else:
            file_path = os.path.join(os.path.dirname(__file__), "assets", "html", "event_selector.html")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return web.Response(text=content, content_type="text/html")
            except FileNotFoundError:
                return web.Response(status=404, text="Default page not found")

    async def handle_view_page(self, request):
        self.logger.info(f"Serving view, {self.event_data_loaded}")
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
            raise web.HTTPFound('/')

    async def handle_set_event_config(self, request):
        data = await request.json()
        self.logger.info(f"Handling set_event_config: {data}")
        self.events.trigger("player.set_event_config", data)
        return web.Response(status=200, text="Done")

    async def handle_sound_test_page(self, request):
        import task_data
        import audio_library
        numbers = [str(n) for n in sorted(audio_library.time_sounds.keys())]
        language_phrases = [
            ("vx_prep_starting",   "Prep starting"),
            ("vx_prep_start",      "Prep started"),
            ("vx_group_sep",       "Group separation"),
            ("vx_round",           "Round"),
            ("vx_group",           "Group"),
            ("vx_1m_to_test",      "1m to test"),
            ("vx_30s_to_test",     "30s to test"),
            ("vx_20s_to_test",     "20s to test"),
            ("vx_test_time",       "Test time"),
            ("vx_1m_to_no_fly",    "1m to no-fly"),
            ("vx_30s_to_no_fly",   "30s to no-fly"),
            ("vx_20s_to_no_fly",   "20s to no-fly"),
            ("vx_no_flying",       "No flying"),
            ("vx_3m_window",       "3m window"),
            ("vx_7m_window",       "7m window"),
            ("vx_10m_window",      "10m window"),
            ("vx_15m_window",      "15m window"),
            ("vx_1m_to_working_time",  "1m to working"),
            ("vx_30s_to_working_time", "30s to working"),
            ("vx_20s_to_working_time", "20s to working"),
            ("vx_30s_landing_window",  "30s landing window"),
        ]
        tasks = [(k, v['name']) for k, v in task_data.f3k_task_timing_data.items()]
        context = {
            'numbers': numbers,
            'language_phrases': language_phrases,
            'tasks': tasks,
        }
        return aiohttp_jinja2.render_template('sound_test.html', request, context=context)

    async def handle_play_sound(self, request):
        import audio_library

        VALID_EFFECTS = {'start_signal', 'countdown_beeps', 'countdown_beeps_3s', 'countdown_beeps_end'}
        VALID_UNITS   = {'second', 'seconds', 'minute', 'minutes'}

        try:
            data = await request.json()
            category = data.get('category', '')
            key      = data.get('key', '')
        except Exception:
            return web.Response(status=400, text='Invalid JSON')

        if category == 'effect':
            if key not in VALID_EFFECTS:
                return web.Response(status=400, text=f'Unknown effect: {key}')
            audio_obj = getattr(audio_library, f'effect_{key}', None)
            if audio_obj is None:
                return web.Response(status=400, text=f'Effect not loaded: {key}')
            self.events.trigger('audioplayer.play_audio', audio_obj)

        elif category == 'number':
            try:
                n = int(key)
            except (ValueError, TypeError):
                return web.Response(status=400, text='Key must be an integer')
            if n not in audio_library.time_sounds:
                return web.Response(status=400, text=f'No sound for number: {n}')
            self.events.trigger('audioplayer.play_integer', n)

        elif category == 'unit':
            if key not in VALID_UNITS:
                return web.Response(status=400, text=f'Unknown unit: {key}')
            self.events.trigger(f'audioplayer.play_literally_{key}')

        elif category == 'language':
            if key not in audio_library.language_audio:
                return web.Response(status=400, text=f'Unknown language key: {key}')
            self.events.trigger('audioplayer.play_audio', audio_library.language_audio[key])

        elif category == 'task':
            if key not in audio_library.task_audio:
                return web.Response(status=400, text=f'Unknown task key: {key}')
            self.events.trigger('audioplayer.play_audio', audio_library.task_audio[key])

        else:
            return web.Response(status=400, text=f'Unknown category: {category}')

        self.logger.info(f'play-sound: {category}/{key}')
        return web.Response(status=200, text='OK')

    async def handle_goto(self, request):
        self.events.trigger(f"player.goto", int(request.match_info['round']), int(request.match_info['group']))
        return web.Response(status=200, text=f"Done")
    
    # Play a series of test sounds to check the audio system is working and the correct voice is loaded
    async def test(self, request):
        import audio_library

        async def wait_for_audio(initial_delay=0.5):
             await asyncio.sleep(initial_delay)
             while pygame.mixer.get_busy():
                    await asyncio.sleep(0.2)

        self.logger.info("Testing audio system with test sounds")
        self.events.trigger(f"audioplayer.play_integer", 5)
        await asyncio.sleep(0.6)
        self.events.trigger(f"audioplayer.play_integer", 19)
        
        await asyncio.sleep(2)

        self.events.trigger(f"audioplayer.play_integer", 8)
        await asyncio.sleep(0.5)
        self.events.trigger(f"audioplayer.play_literally_minutes")           
        
        await asyncio.sleep(2)

        test_sounds = [
            audio_library.effect_start_signal,
            audio_library.effect_countdown_beeps,
            audio_library.effect_countdown_beeps_3s,
            audio_library.effect_countdown_beeps_end,
        ]
        for audio in test_sounds:
            self.events.trigger(f"audioplayer.play_audio", audio)
            await wait_for_audio()
            await asyncio.sleep(1)

        import random
        for audio in random.sample(list(audio_library.language_audio.values()), min(3, len(audio_library.language_audio))):
            self.events.trigger(f"audioplayer.play_audio", audio)
            await wait_for_audio()
            await asyncio.sleep(1)
       
        for audio in random.sample(list(audio_library.task_audio.values()), min(3, len(audio_library.task_audio))):
            self.events.trigger(f"audioplayer.play_audio", audio)
            await wait_for_audio()
            await asyncio.sleep(1)


        return web.Response(status=200, text="Test sounds played")
    
    async def handle_control(self, request):
        self.events.trigger(f"player.{request.match_info['command']}")
        if request.match_info['command']=="reset":
            self.event_data_loaded = False
            raise web.HTTPFound('/')
        return web.Response(status=200, text=f"Done")
    
    async def startup(self):
        self.runner = web.AppRunner(self.app)
        aiohttp_jinja2.setup(
            self.app, loader=jinja2.FileSystemLoader(os.path.join(os.getcwd(), "assets/html"))
            )
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
        if ((not self.limit_rate(state)) and state and state.section):
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

            for q in list(self.client_queues):
                q.put_nowait((js, "groupData"))

    async def onNewRound(self, state):
        if ((not self.limit_rate(state)) and state and state.round):
            d = {}
            d['round_number'] = state.round.round_number
            d['group_count'] = state.round.group_count
            d['task'] = {
            'short_code': state.round.short_code,
            'short_name': state.round.short_name,
            'name': state.round.task_name,
            'description': state.round.task_description,
            }
            self.roundDict = d
            js = json.dumps(d)

            for q in list(self.client_queues):
                q.put_nowait((js, "roundData"))
