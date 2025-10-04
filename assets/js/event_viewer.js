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

  // Fetch /groupData once on page load
  fetch('/groupData')
    .then(response => {
      if (!response.ok) throw new Error('Network response was not ok');
      return response.json();
    })
    .then(data => {
      handlegroupData(data);
    })
    .catch(error => {
      console.warn('Failed to fetch /groupData on load:', error);
    });

  // Periodically poll /groupData every 5 seconds
  setInterval(() => {
    fetch('/groupData')
      .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
      })
      .then(data => {
        handlegroupData(data);
      })
      .catch(error => {
        console.warn('Failed to fetch /groupData:', error);
      });
  }, 5000);
}

function handleMessageByType(type, data) {
  switch (type) {
    case 'time':
      handleTime(data);
      break;
    case 'groupData':
      handlegroupData(data);
      break;
    case 'roundData':
      handleroundData(data);
      break;

    default:
      console.warn('Unhandled message type:', type, data);
  }
}

function handleTime(data) {
  //document.getElementById('wsRXMessage').value = JSON.stringify(data);
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
  // Expecting data.pilots to be an array of pilot objects or names
  const pilots = data.pilots || [];
  const pilotList = document.getElementById('pilotList');
  if (!pilotList) return;
  // Clear previous items
  pilotList.innerHTML = '';
  pilots.forEach((pilot) => {
    const pilotName = typeof pilot === 'string' ? pilot : pilot.name || 'Unknown';
    const li = document.createElement('li');
    li.className = 'list-group-item text-center fw-bold fs-2';
    li.textContent = pilotName;
    pilotList.appendChild(li);
  });
}
function handleroundData(data) {
  console.log(JSON.stringify(data));
}