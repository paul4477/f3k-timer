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

  document.getElementById('bigTime').textContent = data.time_s;
  document.getElementById('roundNum').textContent = data.r_num;
  document.getElementById('groupLetter').textContent = data.g_let;
  // Only append flight number if > 1, unless task_name starts with "F3K Task C"
  let showFlightNum = false;
  if ("f_num" in data && !isNaN(parseInt(data.f_num))) {
    const flightNum = parseInt(data.f_num);
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
  document.getElementById('sectionDescription').textContent = data.sect;

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

async function handleSetConfigButton() {
  const prep_time = document.getElementById('prep_time').value;
  const group_separation_time = document.getElementById('group_separation_time').value;
  const use_strict_test_time = document.getElementById('use_strict_test_time').checked;
  const competition_start_time = document.getElementById('competition_start_time').value;

  try {
    const response = await fetch('/set_event_config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prep_time: parseInt(prep_time),
        group_separation_time: parseInt(group_separation_time),
        use_strict_test_time: use_strict_test_time,
        competition_start_time: parseInt(competition_start_time)
      })
    });
    if (!response.ok) {
      console.error(`Error: ${response.status} ${response.statusText}`);
    }
  } catch (err) {
    console.error(`Error sending config: ${err}`);
  }
}

async function handleGoToButton() {
  const roundValue = document.getElementById('roundSelect').value;
  const groupValue = document.getElementById('groupSelect').value;
  const endpoint = `/goto/${roundValue}/${groupValue}`;
  
  // Add confirmation for quit button
  
    if (!confirm('Are you sure?')) {
      return; // User cancelled, don't proceed
    }
  

  try {
    const response = await fetch(endpoint, {
      method: 'GET'
    });
    
    if (!response.ok) {
      console.error(`Error: ${response.status} ${response.statusText}`);
    }
  } catch (err) {
    console.error(`Error making request to ${endpoint}: ${err}`);
  }
};

// General event handler for control buttons
async function handleControlButton(event) {
  const button = event.target.closest('button');
  
  // Add confirmation for quit button
  if (button.id === 'quit' || button.id === 'reset') {
    if (!confirm('Are you sure?')) {
      return; // User cancelled, don't proceed
    }
  }

  if (button.id === 'start') {
    button.disabled = true; // Disable start button immediately
  }

  const endpoint = `/control/${button.id}`;
  
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      body: {}
    });
    
    if (!response.ok) {
      console.error(`Error: ${response.status} ${response.statusText}`);
    }

   if (button.id === 'reset') {
    location.reload()
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
document.getElementById('reset').addEventListener('click', handleControlButton);

// Add this to your onBodyLoad() function or wherever you set up event listeners
document.getElementById('goto').addEventListener('click', handleGoToButton);
  document.getElementById('prep_time').addEventListener('change', handleSetConfigButton);
  document.getElementById('group_separation_time').addEventListener('change', handleSetConfigButton);
  document.getElementById('competition_start_time').addEventListener('change', handleSetConfigButton);
  document.getElementById('use_strict_test_time').addEventListener('change', handleSetConfigButton);
}





