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
        handleMessageByType(data.type, data.payload);
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

  // Quit button click handler
  document.getElementById('quitBtn').onclick = function () {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send('{"command":"quit"}');
    } else {
      alert('WebSocket is not connected.');
    }
  };
  // Start button click handler
  document.getElementById('startBtn').onclick = function (e) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send('{"command":"start"}');
    } else {
      alert('WebSocket is not connected.');
    }
    // Disable the button
    e.target.closest("button").disabled = true;
  };
  // Pause button click handler
  document.getElementById('pauseBtn').onclick = function () {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send('{"command":"pause"}');
    } else {
      alert('WebSocket is not connected.');
    }
  };
  // FWD button click handler
  document.getElementById('skip_fwdBtn').onclick = function () {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send('{"command":"skip_fwd"}');
    } else {
      alert('WebSocket is not connected.');
    }
  };
  // Next button click handler
  document.getElementById('skip_nextBtn').onclick = function () {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send('{"command":"skip_next"}');
    } else {
      alert('WebSocket is not connected.');
    }
  };
  // REW button click handler
  document.getElementById('skip_backBtn').onclick = function () {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send('{"command":"skip_back"}');
    } else {
      alert('WebSocket is not connected.');
    }
  };
  // Back button click handler
  document.getElementById('skip_previousBtn').onclick = function () {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send('{"command":"skip_previous"}');
    } else {
      alert('WebSocket is not connected.');
    }
  };
}

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
