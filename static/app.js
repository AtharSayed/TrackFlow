// === Initialization ===
document.addEventListener('DOMContentLoaded', () => {
    const BACKEND_URL = window.location.origin;
    const socket = io(BACKEND_URL);

    // --- DOM Elements ---
    // Connection
    const connectionStatusDiv = document.getElementById('connection-status');
    // Registration
    const registrationForm = document.getElementById('registration-form');
    const registerButton = document.getElementById('register-button');
    const registerFeedbackDiv = document.getElementById('register-feedback');
    const qrDisplayContainer = document.getElementById('qr_display_container');
    const qrCodeImg = document.getElementById('qr_code_img');
    const qrDownloadLink = document.getElementById('qr_download_link');
    // Scan
    const scanButton = document.getElementById('scan-button');
    const scanLocationInput = document.getElementById('scan-location');
    const scanFeedbackDiv = document.getElementById('scan-feedback');
    const scannedDataArea = document.getElementById('scanned-data-area');
    const scannedDataContent = document.getElementById('scanned-data-content');
    const initiateReportButton = document.getElementById('initiate-report-button');
    // Report
    const reportFormArea = document.getElementById('report-form-area');
    const reportForm = document.getElementById('report-form');
    const reportPersonNameDisplay = document.getElementById('report-person-name-display');
    const reportLocationInput = document.getElementById('report-location');
    const reportDetailsInput = document.getElementById('report-details');
    const reporterNameInput = document.getElementById('reporter-name');
    const reporterContactInput = document.getElementById('reporter-contact');
    const submitReportButton = document.getElementById('submit-report-button');
    const cancelReportButton = document.getElementById('cancel-report-button');
    const reportFeedbackDiv = document.getElementById('report-feedback');
    // Feeds
    const notificationList = document.getElementById('notification-list');
    const reportListBody = document.getElementById('report-list-body');
    const reportCountSpan = document.getElementById('report-count');
    const refreshReportsButton = document.getElementById('refresh-reports-button');

    // --- State ---
    let lastScannedUserData = null;

    // --- Helper Functions ---
    function displayFeedback(element, message, type = 'info') {
        if (!element) return;
        element.textContent = message;
        element.className = `feedback-message ${type}`; // Use type for class (error, success, info)
        element.style.display = message ? 'block' : 'none';
    }

    function updateConnectionStatus(status) {
        if (!connectionStatusDiv) return;
        connectionStatusDiv.textContent = status;
        connectionStatusDiv.className = `status-${status.toLowerCase()}`;
    }

    function addNotification(message, type = 'info') {
        // (Same addNotification function as in the previous 'app.js' example)
        const li = document.createElement('li');
        li.className = `notification notification-${type}`;
        const timestampSpan = document.createElement('span');
        timestampSpan.className = 'timestamp';
        timestampSpan.textContent = new Date().toLocaleTimeString();
        const messageSpan = document.createElement('span');
        messageSpan.className = 'message';
        messageSpan.textContent = message;
        li.appendChild(timestampSpan);
        li.appendChild(messageSpan);
        const placeholder = notificationList.querySelector('.placeholder');
        if (placeholder) placeholder.remove();
        notificationList.insertBefore(li, notificationList.firstChild);
        while (notificationList.children.length > 50) notificationList.removeChild(notificationList.lastChild);
    }

    function formatDateTime(isoString) {
        // (Same formatDateTime function as before)
        if (!isoString) return 'N/A';
        try { return new Date(isoString).toLocaleString(); }
        catch (e) { return isoString; }
    }

    // --- Report List Rendering ---
     function renderReports(reports = []) {
        reportListBody.innerHTML = ''; // Clear existing rows
        if (reports.length === 0) {
            reportListBody.innerHTML = '<tr class="placeholder-row"><td colspan="4">No reports found.</td></tr>';
        } else {
            reports.forEach(addReportRow);
        }
        reportCountSpan.textContent = reports.length;
    }

    function addReportRow(report) {
        // Simplified for this example - only key fields
        const row = document.createElement('tr');
        row.className = `report-status-${report.status?.toLowerCase()}`;
        row.dataset.reportId = report.report_id;

        row.innerHTML = `
            <td><span class="status-badge status-${report.status?.toLowerCase()}">${report.status || 'UNKNOWN'}</span></td>
            <td>${report.person_name || 'N/A'}</td>
            <td>${report.last_known_location || 'N/A'}</td>
            <td>${formatDateTime(report.report_time)}</td>
        `;
        // (Add logic to remove placeholder and update/prepend row as before)
         const placeholder = reportListBody.querySelector('.placeholder-row');
         if (placeholder) placeholder.remove();
         const existingRow = reportListBody.querySelector(`tr[data-report-id="${report.report_id}"]`);
         if (existingRow) {
             reportListBody.replaceChild(row, existingRow);
         } else {
             reportListBody.insertBefore(row, reportListBody.firstChild);
         }
    }

     async function fetchInitialReports() {
         try {
             addNotification('Fetching reports...', 'info');
             const response = await fetch(`${BACKEND_URL}/api/reports`);
             if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
             const reports = await response.json();
             renderReports(reports);
         } catch (error) {
             console.error('Error fetching reports:', error);
             addNotification(`Error fetching reports: ${error.message}`, 'error');
             reportListBody.innerHTML = '<tr class="placeholder-row"><td colspan="4">Error loading reports.</td></tr>';
         }
     }


    // --- WebSocket Event Handlers ---
    socket.on('connect', () => {
        updateConnectionStatus('Connected');
        addNotification('Connected to real-time server.', 'success');
        fetchInitialReports();
    });
    socket.on('disconnect', () => {
        updateConnectionStatus('Disconnected');
        addNotification('Disconnected from real-time server.', 'error');
        hideScanAndReportAreas(); // Hide relevant areas on disconnect
    });
    socket.on('connect_error', () => updateConnectionStatus('Disconnected'));
    socket.on('welcome', (data) => addNotification(data.message, 'info'));

    // Registration
    socket.on('new_registration', (data) => {
        addNotification(data.message, 'success');
        displayFeedback(registerFeedbackDiv, data.message, 'success');
        if (data.user?.qr_code_path) {
            qrCodeImg.src = data.user.qr_code_path;
            qrDownloadLink.href = data.user.qr_code_path;
            qrDisplayContainer.style.display = 'block';
        }
    });
    socket.on('registration_error', (data) => {
        addNotification(data.message, 'error');
        displayFeedback(registerFeedbackDiv, data.message, 'error');
        qrDisplayContainer.style.display = 'none';
    });

    // Scan
    socket.on('scan_result', (data) => {
        addNotification(data.message, data.success ? 'success' : 'error');
        displayFeedback(scanFeedbackDiv, data.message, data.success ? 'success' : 'error');
        if (data.success && data.data?.scanned_user_data) {
            lastScannedUserData = data.data.scanned_user_data; // Store the full user object
            displayScannedData(lastScannedUserData);
            scannedDataArea.style.display = 'block';
            reportFormArea.style.display = 'none'; // Hide report form initially
        } else {
            hideScanAndReportAreas(); // Hide areas if scan fails
        }
    });

    // Report
    socket.on('new_report', (data) => {
        addNotification(data.message, 'warning');
        addReportRow(data.report);
        reportCountSpan.textContent = reportListBody.querySelectorAll('tr:not(.placeholder-row)').length;
    });
    socket.on('report_error', (data) => {
        addNotification(data.message, 'error');
        displayFeedback(reportFeedbackDiv, data.message, 'error'); // Show error on report form
    });

     // Alerts (Example)
    socket.on('density_warning', (data) => addNotification(data.message, 'alert'));
    socket.on('anomaly', (data) => addNotification(data.message, 'alert'));
    socket.on('person_located', (data) => {
        addNotification(data.message, 'success');
        // Optionally update the specific report row's status visually
        fetchInitialReports(); // Easiest way to refresh list with updated status
    });


    // --- UI Update Functions ---
    function displayScannedData(userData) {
        let content = `<strong>Name:</strong> ${userData.name || 'N/A'}<br>
                       <strong>Phone:</strong> ${userData.phone || 'N/A'}<br>
                       <strong>Address:</strong> ${userData.address || 'N/A'}`;

        if (userData.family_members && userData.family_members.length > 0) {
            content += '<br><br><strong>Family:</strong><ul>';
            userData.family_members.forEach(m => {
                content += `<li>${m.name} (${m.phone})${m.relation === 'child' ? ` <i>(Child - Age: ${m.age}, ${m.gender})</i>` : ''}</li>`;
            });
            content += '</ul>';
        }
         if (userData.friends && userData.friends.length > 0) {
            content += '<strong>Friends:</strong><ul>';
            userData.friends.forEach(f => {
                content += `<li>${f.name} (${f.phone})</li>`;
            });
            content += '</ul>';
        }
        scannedDataContent.innerHTML = content;
    }

    function hideScanAndReportAreas() {
        scannedDataArea.style.display = 'none';
        reportFormArea.style.display = 'none';
        lastScannedUserData = null;
    }

    // --- Event Listeners ---

    // Registration Form Submission
    registrationForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        registerButton.disabled = true;
        registerButton.textContent = 'Registering...';
        displayFeedback(registerFeedbackDiv, ''); // Clear previous feedback
        qrDisplayContainer.style.display = 'none';

        const name = document.getElementById('reg-name').value;
        const phone = document.getElementById('reg-phone').value;
        const address = document.getElementById('reg-address').value;
        const familyMembers = collectMembers('family');
        const friends = collectMembers('friend');

        const payload = { name, phone, address, family_members: familyMembers, friends: friends };

        try {
            const response = await fetch(`${BACKEND_URL}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json(); // Needed to check response.ok
            if (!response.ok) throw new Error(result.error || `HTTP error ${response.status}`);
            // Success is handled by WebSocket 'new_registration'
            registrationForm.reset(); // Reset form fields on successful request
             // Clear dynamic members manually
             document.getElementById('family_members_container').innerHTML = '';
             document.getElementById('friend_members_container').innerHTML = '';

        } catch (error) {
            console.error('Registration fetch error:', error);
            if (!socket.connected) { // Fallback if WS disconnected
                displayFeedback(registerFeedbackDiv, `Error: ${error.message}`, 'error');
            }
            // Error should also be handled by WebSocket 'registration_error'
        } finally {
            registerButton.disabled = false;
            registerButton.textContent = 'Register';
        }
    });

    // Scan Button
    scanButton.addEventListener('click', async () => {
        scanButton.disabled = true;
        scanButton.textContent = 'Scanning...';
        hideScanAndReportAreas(); // Clear previous scan/report state
        displayFeedback(scanFeedbackDiv, 'Attempting Scan... Check Server Camera.', 'info');

        try {
            const location = scanLocationInput.value || 'Unknown';
            const response = await fetch(`${BACKEND_URL}/scan_qr?location=${encodeURIComponent(location)}`);
            const result = await response.json(); // Wait for scan attempt
             if (!response.ok) throw new Error(result.error || `Scan trigger failed`);
             // Result (success or error) handled primarily by WebSocket 'scan_result'
        } catch (error) {
             console.error('Scan trigger error:', error);
             if (!socket.connected) { // Fallback
                 displayFeedback(scanFeedbackDiv, `Error: ${error.message}`, 'error');
             }
        } finally {
             scanButton.disabled = false;
             scanButton.textContent = 'Start Scan';
        }
    });

     // Initiate Report Button (after successful scan)
     initiateReportButton.addEventListener('click', () => {
         if (lastScannedUserData) {
             reportPersonNameDisplay.textContent = lastScannedUserData.name || 'N/A';
             reportForm.reset(); // Clear previous report form inputs
             displayFeedback(reportFeedbackDiv, ''); // Clear previous report feedback
             reportFormArea.style.display = 'block'; // Show the form
             scannedDataArea.style.display = 'none'; // Hide the scanned data display
         }
     });


    // Report Form Submission
    reportForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!lastScannedUserData) {
            displayFeedback(reportFeedbackDiv, 'No scanned user data available.', 'error');
            return;
        }
        submitReportButton.disabled = true;
        submitReportButton.textContent = 'Submitting...';
        displayFeedback(reportFeedbackDiv, '');

        const payload = {
            scanned_user_data: lastScannedUserData, // The full user object
            last_known_location: reportLocationInput.value,
            additional_details: reportDetailsInput.value,
            reporter_name: reporterNameInput.value || 'Anonymous',
            reporter_contact: reporterContactInput.value
        };

        try {
            const response = await fetch(`${BACKEND_URL}/submit_report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || `HTTP error ${response.status}`);
             // Success feedback
            addNotification(`Report submitted for ${lastScannedUserData.name}.`, 'success');
            hideScanAndReportAreas(); // Hide form area
            reportForm.reset(); // Clear form

        } catch (error) {
            console.error('Report submit error:', error);
            if (!socket.connected) { // Fallback
                displayFeedback(reportFeedbackDiv, `Error: ${error.message}`, 'error');
            }
            // Error also handled by WebSocket 'report_error'
        } finally {
            submitReportButton.disabled = false;
            submitReportButton.textContent = 'Submit Report';
        }
    });

    // Cancel Report Button
    cancelReportButton.addEventListener('click', () => {
        reportFormArea.style.display = 'none';
        reportForm.reset();
        // Show scanned data again if available
        if (lastScannedUserData) {
            scannedDataArea.style.display = 'block';
        }
    });

    // Refresh Reports Button
    refreshReportsButton.addEventListener('click', fetchInitialReports);

    // --- Dynamic Member Functions ---
    // Make these functions globally accessible for onclick handlers
    window.addMember = function(type) {
        let container = document.getElementById(type + "_members_container");
        if (!container) return;
        let div = document.createElement("div");
        div.classList.add("member-container");

        // Unique IDs might be needed if selecting specific child inputs later
        const uniqueId = type + '_' + Date.now(); // Simple unique ID

        div.innerHTML = `
            <input type="text" placeholder="${type.charAt(0).toUpperCase() + type.slice(1)} Name *" class="${type}-name" required>
            <input type="tel" placeholder="Phone *" class="${type}-phone" required>
            ${type === 'family' ? `
            <label>
                <input type="checkbox" class="child-checkbox" onchange="toggleChildDetails(this)"> Is this a child?
            </label>
            <div class="child-details" style="display: none;">
                <input type="number" placeholder="Age" class="child-age">
                <input type="text" placeholder="Gender" class="child-gender">
                <input type="text" placeholder="Description (Clothing, etc.)" class="child-description">
            </div>` : ''}
            <button type="button" class="remove-btn" onclick="removeMember(this)">Remove</button>
        `;
        container.appendChild(div);
    };

    window.toggleChildDetails = function(checkbox) {
        // Find the child-details div relative to the checkbox's parent container
        let childDetailsDiv = checkbox.closest('.member-container').querySelector('.child-details');
        if (childDetailsDiv) {
            childDetailsDiv.style.display = checkbox.checked ? "block" : "none";
        }
    };

    window.removeMember = function(button) {
        button.closest('.member-container').remove();
    };

    // Function to collect member data before submitting registration
    function collectMembers(type) {
        const members = [];
        const container = document.getElementById(type + '_members_container');
        if (!container) return members;

        container.querySelectorAll('.member-container').forEach(div => {
            const nameInput = div.querySelector(`.${type}-name`);
            const phoneInput = div.querySelector(`.${type}-phone`);
            if (nameInput && phoneInput && nameInput.value.trim() && phoneInput.value.trim()) {
                const memberData = {
                    name: nameInput.value.trim(),
                    phone: phoneInput.value.trim()
                };
                if (type === 'family') {
                    const isChildCheckbox = div.querySelector('.child-checkbox');
                    if (isChildCheckbox && isChildCheckbox.checked) {
                        memberData.is_child = true; // Add flag for backend processing
                        memberData.age = div.querySelector('.child-age')?.value || null;
                        memberData.gender = div.querySelector('.child-gender')?.value || null;
                        memberData.description = div.querySelector('.child-description')?.value || null;
                    }
                }
                members.push(memberData);
            }
        });
        return members;
    }

    // --- Initial Page Load ---
    updateConnectionStatus('Connecting'); // Set initial status


}); // End DOMContentLoaded