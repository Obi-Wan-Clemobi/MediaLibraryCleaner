function appData() {
    return {
        currentView: 'dashboard',
        stats: {
            total_files: 0,
            tv_files: 0,
            movie_files: 0,
            total_issues: 0,
            duplicates: 0,
            low_res: 0
        },
        files: [],
        issues: [],
        issueFilter: 'all',
        scanning: false,
        analyzing: false,
        scanProgress: 0,
        scanStatus: '',
        socket: null,

        init() {
            this.loadStats();
            this.loadFiles();
            this.loadIssues();
            this.initSocket();
        },

        initSocket() {
            this.socket = io();

            this.socket.on('scan_progress', (data) => {
                this.scanProgress = Math.min((data.progress / 100) * 100, 90);
                this.scanStatus = data.status;
            });

            this.socket.on('scan_complete', (data) => {
                this.scanning = false;
                this.scanProgress = 100;
                this.scanStatus = `Complete! Scanned ${data.total} files`;
                this.loadStats();
                this.loadFiles();
                setTimeout(() => {
                    this.scanProgress = 0;
                    this.scanStatus = '';
                }, 3000);
            });

            this.socket.on('analyze_progress', (data) => {
                this.scanStatus = data.status;
            });

            this.socket.on('analyze_complete', (data) => {
                this.analyzing = false;
                this.scanStatus = `Analysis complete! Found ${data.total_issues} issues`;
                this.loadStats();
                this.loadIssues();
                setTimeout(() => {
                    this.scanStatus = '';
                }, 3000);
            });
        },

        async loadStats() {
            const response = await fetch('/api/stats');
            this.stats = await response.json();
        },

        async loadFiles() {
            const response = await fetch('/api/files');
            this.files = await response.json();
        },

        async loadIssues(type = null) {
            const url = type ? `/api/issues?type=${type}` : '/api/issues';
            const response = await fetch(url);
            this.issues = await response.json();
        },

        async triggerScan() {
            this.scanning = true;
            this.scanProgress = 0;
            await fetch('/api/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paths: [] })
            });
        },

        async triggerAnalyze() {
            this.analyzing = true;
            await fetch('/api/analyze', { method: 'POST' });
        },

        filterIssues(type) {
            this.issueFilter = type;
            if (type === 'all') {
                this.loadIssues();
            } else {
                this.loadIssues(type);
            }
        },

        get filteredIssues() {
            return this.issues;
        },

        formatBytes(bytes) {
            if (!bytes) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
        }
    }
}
