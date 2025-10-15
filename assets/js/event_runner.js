let socket;
let reconnectInterval = 2000; // ms
let reconnectTimeout;

// Create EventSource connection for state updates
const eventSource = new EventSource('/state-stream');
const bigTime = document.getElementById('bigTime');

// Handle incoming general messages
eventSource.onmessage = function(event) {
  // For now lets just put it up for debugging
  //console.log(event.data);
    
};

eventSource.addEventListener("groupData", (event) => {
  console.log(event.data);
});
eventSource.addEventListener("roundData", (event) => {
  console.log(event.data);
});

eventSource.addEventListener("time", (event) => {
  //console.log("Time event received:");
  //console.log(typeof event.data);
  data = JSON.parse(event.data);

  document.getElementById('wsRXMessage').value = event.data;
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
});

// General event handler for control buttons
async function handleControlButton(event) {
  const buttonId = event.target.closest('button').id;
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
function onBodyLoad() {  
document.getElementById('start').addEventListener('click', handleControlButton);
document.getElementById('pause').addEventListener('click', handleControlButton);
document.getElementById('skip_fwd').addEventListener('click', handleControlButton);

document.getElementById('skip_next').addEventListener('click', handleControlButton);
document.getElementById('skip_back').addEventListener('click', handleControlButton);
document.getElementById('skip_previous').addEventListener('click', handleControlButton); 
document.getElementById('quit').addEventListener('click', handleControlButton); 
}




