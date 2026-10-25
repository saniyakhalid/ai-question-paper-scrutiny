import api from '../services/api';

/**
 * Downloads a scrutiny report in the specified format (pdf, csv, json)
 * using authenticated Axios requests with blob responses.
 * Avoids browser popup blockers and preserves Authorization Bearer token headers.
 */
export async function downloadScrutinyReport(paperId, format = 'pdf', title = 'Scrutiny_Report') {
  try {
    const fmt = format.toLowerCase();
    const endpoint = `/scrutiny/reports/${paperId}/export/${fmt}`;
    const response = await api.get(endpoint, {
      responseType: 'blob',
    });

    const mimeTypes = {
      pdf: 'application/pdf',
      csv: 'text/csv',
      json: 'application/json',
    };

    const blob = new Blob([response.data], {
      type: mimeTypes[fmt] || 'application/octet-stream',
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const sanitizedTitle = (title || `Paper_${paperId}`).replace(/[^a-zA-Z0-9_-]/g, '_');
    link.setAttribute('download', `${sanitizedTitle}_Report.${fmt}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    return { ok: true };
  } catch (error) {
    console.error(`Failed to export ${format} report:`, error);
    throw error;
  }
}

/**
 * Downloads moderator feedback dataset in CSV or JSON format.
 */
export async function downloadModeratorDataset(format = 'csv') {
  try {
    const fmt = format.toLowerCase();
    const response = await api.get(`/moderator/feedback/export?format=${fmt}`, {
      responseType: 'blob',
    });
    const mimeTypes = {
      csv: 'text/csv',
      json: 'application/json',
    };
    const blob = new Blob([response.data], {
      type: mimeTypes[fmt] || 'application/octet-stream',
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `moderator_feedback_dataset.${fmt}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    return { ok: true };
  } catch (error) {
    console.error(`Failed to export moderator dataset:`, error);
    throw error;
  }
}
