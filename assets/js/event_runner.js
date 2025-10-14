let socket;
let reconnectInterval = 2000; // ms
let reconnectTimeout;

function connectWebSocket() {
  socket = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/');

  socket.onopen = function (event) {
    console.log('WebSocket connection opened:', event);
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
  };

  socket.onmessage = function (event) {
    try {
      const data = JSON.parse(event.data);
      if (data && data.type) {
        handleMessageByType(data.type, data.data);
      } else {
        console.warn('Received message without type:', data);
      }
    } catch (e) {
      console.error('Failed to parse message:', event.data, e);
    }
  };

  socket.onclose = function (event) {
    console.warn('WebSocket closed. Attempting to reconnect...');
    scheduleReconnect();
  };

  socket.onerror = function (event) {
    console.error('WebSocket error:', event);
    socket.close();
  };
}

function scheduleReconnect() {
  if (!reconnectTimeout) {
    reconnectTimeout = setTimeout(() => {
      connectWebSocket();
    }, reconnectInterval);
  }
}

function onBodyLoad() {
  connectWebSocket();
  // Button click handler
  document.getElementById('sendBtn').onclick = function () {
    const msg = document.getElementById('wsTXMessage').value;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(msg);
    } else {
      alert('WebSocket is not connected.');
    }
  };

  // General event handler for control buttons
async function handleControlButton(event) {
  const buttonId = event.target.id;
  const endpoint = `/control/${buttonId}`;
  
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      body: {}
    });
    
    if (!response.ok) {
      console.error(`Error: ${response.status} ${response.statusText}`);
    }
  } catch (err) {
    console.error(`Error making request to ${endpoint}: ${err}`);
  }
}
  
document.getElementById('start').addEventListener('click', handleControlButton);
document.getElementById('pause').addEventListener('click', handleControlButton);
document.getElementById('skip_fwd').addEventListener('click', handleControlButton);

document.getElementById('skip_next').addEventListener('click', handleControlButton);
document.getElementById('skip_back').addEventListener('click', handleControlButton);
document.getElementById('skip_previous').addEventListener('click', handleControlButton); 

  // Quit button click handler
  document.getElementById('quitBtn').onclick = function () {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send('{"command":"quit"}');
    } else {
      alert('WebSocket is not connected.');
    }
  };



function handleMessageByType(type, data) {
  switch (type) {
    case 'time':
      handleTime(data);
      break;
    case 'groupData':
      handlegroupData(data);
      break;
    default:
      console.warn('Unhandled message type:', type, data);
  }
}

function handleTime(data) {
  document.getElementById('wsRXMessage').value = JSON.stringify(data);
  document.getElementById('bigTime').textContent = data.time_str;
  document.getElementById('roundNum').textContent = data.round_num;
  document.getElementById('groupLetter').textContent = data.group_let;
  // Only append flight number if > 1, unless task_name starts with "F3K Task C"
  let showFlightNum = false;
  if ("flight_num" in data && !isNaN(parseInt(data.flight_num))) {
    const flightNum = parseInt(data.flight_num);
    if (
      (flightNum > 1) ||
      (typeof data.task_name === "string" && data.task_name.startsWith("F3K Task C"))
    ) {
      showFlightNum = true;
    }
    if (showFlightNum) {
      document.getElementById('groupLetter').textContent += ` (${flightNum})`;
    }
  }
  document.getElementById('roundDescription').textContent = data.task_name;
  document.getElementById('sectionDescription').textContent = data.section;

  const nameRow = document.getElementById('roundNameRow')
  const numRow = document.getElementById('roundNumRow')
  const sectionRow = document.getElementById('sectionRow')

  if (data.no_fly && nameRow.classList.contains('bg-success')) {
    nameRow.classList.remove('bg-success');
    nameRow.classList.add('bg-danger');
    numRow.classList.remove('bg-success');
    numRow.classList.add('bg-danger');
    sectionRow.classList.remove('bg-success');
    sectionRow.classList.add('bg-danger');
  }
  else {
    if (!data.no_fly && nameRow.classList.contains('bg-danger')) {
      nameRow.classList.remove('bg-danger');
      nameRow.classList.add('bg-success');
      numRow.classList.remove('bg-danger');
      numRow.classList.add('bg-success');
      sectionRow.classList.remove('bg-danger');
      sectionRow.classList.add('bg-success');
    }
  }
}

function handlegroupData(data) {
  console.log(JSON.stringify(data));
}
function handleroundData(data) {
  console.log(JSON.stringify(data));
}