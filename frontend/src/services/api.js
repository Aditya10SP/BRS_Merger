import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Health check
export const healthCheck = async () => {
    const response = await api.get('/health');
    return response.data;
};

// Get system stats
export const getStats = async () => {
    const response = await api.get('/stats');
    return response.data;
};

// Upload BRS document
export const uploadBRS = async (file, docId = null, version = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (docId) formData.append('doc_id', docId);
    if (version) formData.append('version', version);

    const response = await api.post('/upload/brs', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

// Upload Change Request
export const uploadCR = async (file, crId = null, priority = 'medium', approvalStatus = 'approved') => {
    const formData = new FormData();
    formData.append('file', file);
    if (crId) formData.append('cr_id', crId);
    formData.append('priority', priority);
    formData.append('approval_status', approvalStatus);

    const response = await api.post('/upload/cr', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

// Start consolidation
export const startConsolidation = async ({ brs_id, title, version, section_outline = null }) => {
    const response = await api.post('/consolidate', {
        brs_id: brs_id,
        title: title,
        version: version,
        section_outline: section_outline,
    });
    return response.data;
};

// Get job status
export const getJobStatus = async (jobId) => {
    const response = await api.get(`/job/${jobId}`);
    return response.data;
};

export const getDownloadUrl = (filename) => {
    if (!filename) return '#';
    // If filename is already a full API path like /api/v1/download/...
    if (filename.startsWith('/api/v1/download/')) {
        return `${API_BASE_URL.replace('/api/v1', '')}${filename}`;
    }
    return `${API_BASE_URL}/download/${filename}`;
};

// Reset vector store
export const resetVectorStore = async () => {
    const response = await api.delete('/reset');
    return response.data;
};

export default api;
