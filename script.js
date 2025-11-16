document.addEventListener('DOMContentLoaded', () => {
    // Get all the elements we'll need
    const dropArea = document.getElementById('drop-area');
    const dropLabel = document.getElementById('drop-label');
    const fileInput = document.getElementById('file-input');
    const analyzeButton = document.getElementById('analyze-button');

    const reportSection = document.getElementById('report-section');
    const loader = document.getElementById('loader');
    const errorMessage = document.getElementById('error-message');
    const results = document.getElementById('results');
    
    // Result fields
    const riskLevel = document.getElementById('risk-level');
    const riskScoreCard = document.getElementById('risk-score-card');
    const infoDeadline = document.getElementById('info-deadline');
    const infoBudget = document.getElementById('info-budget');
    const infoContact = document.getElementById('info-contact');
    const riskList = document.getElementById('risk-list');
    const summaryText = document.getElementById('summary-text');

    let selectedFile = null;

    // --- Event Listeners ---

    // Drag and Drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.add('dragging'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.remove('dragging'), false);
    });

    dropArea.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', handleFileSelect);
    analyzeButton.addEventListener('click', handleAnalyze);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // --- File Handling ---

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    }

    function handleFileSelect(e) {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    }

    function handleFile(file) {
        if (file && file.type === 'application/pdf') {
            selectedFile = file;
            dropLabel.innerHTML = `<span class="drop-icon">✅</span> <strong>File selected:</strong> ${file.name}`;
            analyzeButton.disabled = false;
        } else {
            selectedFile = null;
            dropLabel.innerHTML = `<span class="drop-icon">❌</span> <strong>Invalid file:</strong> Please select a PDF.`;
            analyzeButton.disabled = true;
        }
    }

    // --- API Call & Analysis ---

    async function handleAnalyze() {
        if (!selectedFile) return;

        // 1. Set UX to "loading" state
        resetReport();
        reportSection.hidden = false;
        loader.hidden = false;

        // 2. Prepare form data
        const formData = new FormData();
        formData.append('pdf_file', selectedFile);

        try {
            // 3. Send file to backend
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Server error');
            }

            // 4. Get JSON data and display it
            const data = await response.json();
            displayReport(data);

        } catch (error) {
            showError(error.message);
        } finally {
            // 5. Hide loader
            loader.hidden = true;
        }
    }
    
    // --- UI Update Functions ---
    
    function displayReport(data) {
        // Set Risk Level and color
        riskLevel.textContent = data.risk_level || 'N/A';
        riskLevel.className = 'risk-level'; // Clear old classes
        if (data.risk_level) {
            riskLevel.classList.add(`risk-${data.risk_level.toLowerCase()}`);
        }

        // Set Extracted Info
        infoDeadline.textContent = data.deadline || 'Not found';
        infoBudget.textContent = data.budget ? data.budget.toLocaleString() : 'Not found';
        infoContact.textContent = data.contact || 'Not found';

        // Set Risks List
        riskList.innerHTML = ''; // Clear default
        if (data.risks && data.risks.length > 0) {
            if (data.risks[0] === "No immediate risks detected") {
                const li = document.createElement('li');
                li.className = 'no-risk';
                li.textContent = data.risks[0];
                riskList.appendChild(li);
            } else {
                data.risks.forEach(risk => {
                    const li = document.createElement('li');
                    li.textContent = risk;
                    riskList.appendChild(li);
                });
            }
        } else {
            const li = document.createElement('li');
            li.className = 'no-risk';
            li.textContent = 'No risks detected.';
            riskList.appendChild(li);
        }

        // Set Summary
        summaryText.textContent = data.summary || 'No summary available.';

        // Show results
        results.hidden = false;
    }

    function showError(message) {
        errorMessage.textContent = `Error: ${message}`;
        errorMessage.hidden = false;
    }

    function resetReport() {
        // Hide all report elements
        loader.hidden = true;
        errorMessage.hidden = true;
        results.hidden = true;
        
        // Reset text content
        riskLevel.textContent = '---';
        infoDeadline.textContent = 'Not found';
        infoBudget.textContent = 'Not found';
        infoContact.textContent = 'Not found';
        riskList.innerHTML = '';
        summaryText.textContent = '';
    }
});
