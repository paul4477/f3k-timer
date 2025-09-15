import asyncio
 
from aiohttp import web
import pygame
 
# async version of pygame.time.Clock
class Clock:
    def __init__(self, time_func=pygame.time.get_ticks):
        self.time_func = time_func
        self.last_tick = time_func() or 0
 
    async def tick(self, fps=0):
        if 0 >= fps:
            return
 
        end_time = (1.0 / fps) * 1000
        current = self.time_func()
        time_diff = current - self.last_tick
        delay = (end_time - time_diff) / 1000
 
        self.last_tick = current
        if delay < 0:
            delay = 0
 
        await asyncio.sleep(delay)
 
 
class EventEngine:
    def __init__(self):
        self.listeners = {}
 
    def on(self, event):
        if event not in self.listeners:
            self.listeners[event] = []
 
        def wrapper(func, *args):
            self.listeners[event].append(func)
            return func
 
        return wrapper
 
    # this function is purposefully not async
    # code calling this will do so in a "fire-and-forget" manner, and shouldn't be slowed down by needing to await a result
    def trigger(self, event, *args, **kwargs):
        asyncio.create_task(self.async_trigger(event, *args, **kwargs))
 
    # whatever gets triggered is just added to the current asyncio event loop, which we then trust to run eventually
    async def async_trigger(self, event, *args, **kwargs):
        if event in self.listeners:
            handlers = [func(*args, **kwargs) for func in self.listeners[event]]
 
            # schedule all listeners to run
            return await asyncio.gather(*handlers)
 
 
events = EventEngine()
 
 
class Player:
    player_count = 0
 
    def __init__(self, color):
        Player.player_count += 1
        self.player_id = Player.player_count
 
        self.surface = self.original_surface = self.create_surface(color)
        self.pos = [10, 10]
        self.movement_intensity = 10
        self.register_handlers()
 
    def create_surface(self, color):
        surf = pygame.Surface((25, 25), pygame.SRCALPHA)
        surf.fill(color)
        return surf
 
    def register_handlers(self):
        events.on(f"input.move_up.{self.player_id}")(self.move_up)
        events.on(f"input.move_right.{self.player_id}")(self.move_right)
 
    async def move_right(self, amount):
        self.pos[0] += amount * self.movement_intensity
 
    async def move_up(self, amount):
        # 0 == top of screen, so 'up' is negative
        self.pos[1] -= amount * self.movement_intensity
 
    async def update(self, window):
        window.blit(self.surface, self.pos)
 
 
class Game:
    player_colors = [(155, 155, 0), (0, 155, 155), (155, 0, 155)]
 
    def __init__(self):
        self.players = []
        events.on("player.add")(self.create_player)
 
    async def create_player(self):
        color = self.player_colors[len(self.players) % len(self.player_colors)]
        new_player = Player(color)
        self.players.append(new_player)
        return new_player
 
    async def update(self, window):
        for player in self.players:
            await player.update(window)
 
 
html_page = """
<html><head>
<script>
 const wsUri = "http://192.168.64.221:8080/get_ticks/";
const socket = new WebSocket(wsUri);
    
          // Button click handler
    function send_message(s) {{

        socket.send(s);  // <-- send message via WebSocket
        console.log("Sent:", s);
        

    }};

function setup() {{



    // When connection opens
    socket.addEventListener("open", () => {{
      console.log("Connected to server.");
      socket.send("Hello from browser!");
    }});

    // When a message arrives
    socket.addEventListener("message", (event) => {{
      console.log("Received:", event.data);

      // Append to page
      const h = document.getElementById("time");
      
      h.textContent = event.data;
      
    }});

    // Handle close
    socket.addEventListener("close", () => {{
      console.log("Connection closed.");
    }});

    // Handle errors
    socket.addEventListener("error", (err) => {{
      console.error("WebSocket error:", err);
    }});



}}
  </script>
</head>"""+"""<body onLoad="setup()"><table>
<tr><td></td><td><a href="/move/{player_id}/up"><button>UP</button></a></td><td></td></tr>
<tr><td><a href="/move/{player_id}/left"><button>LEFT</button></td>
    <td></td>
    <td><a href="/move/{player_id}/right"><button>RIGHT</button></td></tr>
<tr><td></td><td><a href="/move/{player_id}/down"><button>DOWN</button></a></td><td></td></tr>



</table>
<h1 id="time">{ticks}</h1>
<button onclick="send_message('r')">WS RIGHT</button>
<div id="messages"></div></body></html>
"""
 
 
class WebFrontend:
    def __init__(self, port=8080):
        self.port = port
        self.runner = None
        self.app = web.Application()
        self.ticks = 0
        self.clients = set()
        self.app.add_routes(
            [
                web.get("/", self.register_new_user),
                web.get("/controls/{player_id}", self.player_controls),
                web.get("/move/{player_id}/{direction}", self.move_player),
                web.get("/get_ticks/", self.ws_handler),
            ]
        )
 
    async def ws_handler(self, request):
        print ("in ws_handler")
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        print ("Client connected:", request.remote, "Total:", len(self.clients))
 
        try:
          async for msg in ws:
            
            if msg.type == web.WSMsgType.TEXT:
                
                if msg.data == 'close':
                  await ws.close()
                else:
                  print(f"Message from client: {msg.data}")
                  events.trigger(f"input.move_right.2", 1)
            elif msg.type == web.WSMsgType.ERROR:
                print(f"WebSocket connection closed with exception {ws.exception()}")
        finally:
          self.clients.remove(ws)
          print("Client disconnected. Total:", len(self.clients))
 
        
        return ws
    
    async def broadcast(self, message):
        for ws in list(self.clients):
            await ws.send_str(message)
    
    async def register_new_user(self, request):
        player = (await events.async_trigger("player.add"))[0]
        raise web.HTTPFound(location=f"/controls/{player.player_id}")
 
    async def player_controls(self, request):
        data = request.match_info["player_id"]
        return web.Response(
            content_type="text/html", body=html_page.format(player_id=data, ticks=self.ticks)
        )
 
    async def move_player(self, request):
        player_id = request.match_info["player_id"]
        action = request.match_info["direction"]
        direction = "right" if action in ("left", "right") else "up"
        power = 1 if action in ("right", "up") else -1
        events.trigger(f"input.move_{direction}.{player_id}", power)
        return await self.player_controls(request)
 
    async def startup(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", 8080)
        await site.start()
 
    async def shutdown(self):
        if self.runner:
            await self.runner.cleanup()

    async def update(self, ticks):
        self.ticks = ticks
        await self.broadcast(str(self.ticks))

duration = 30
async def main():
    window = pygame.display.set_mode((500, 500))
    web_server = WebFrontend()
    await web_server.startup()
 
    game = Game()
    # add a local player
    local_player = (await events.async_trigger("player.add"))[0]
    local_player_id = local_player.player_id
    
    countdown_start = pygame.time.get_ticks()
    last_countdown = 0
    
    clock = Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return
 
            # handlers for a local player using keyboard
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_LEFT:
                    events.trigger(f"input.move_right.{local_player_id}", -1)
                elif ev.key == pygame.K_RIGHT:
                    events.trigger(f"input.move_right.{local_player_id}", +1)
                elif ev.key == pygame.K_UP:
                    events.trigger(f"input.move_up.{local_player_id}", +1)
                elif ev.key == pygame.K_DOWN:
                    events.trigger(f"input.move_up.{local_player_id}", -1)
                elif ev.key == pygame.K_SPACE:
                    await web_server.broadcast("Hello from server!")
 
        window.fill((0, 0, 0))
        await game.update(window)
        pygame.display.flip()
        
        #await web_server.update(pygame.time.get_ticks())
        
        countdown = duration - int((pygame.time.get_ticks() - countdown_start)/1000)

        if countdown >= 0: #elif True:#event.type == TIMEREVENT:
              countdown = duration - int((pygame.time.get_ticks() - countdown_start)/1000)
              if countdown != last_countdown:        
                  await web_server.update(countdown)
                  last_countdown = countdown
        await clock.tick(30)
 
 
if __name__ == "__main__":
    pygame.init()
    asyncio.run(main())
    pygame.quit()