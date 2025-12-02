import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { 
  CheckCircle, 
  XCircle, 
  Edit, 
  Users, 
  AlertTriangle,
  Clock,
  BarChart
} from 'lucide-react';

interface ApprovalRequest {
  task_id: string;
  task_description: string;
  decision: string;
  confidence: number;
  risk_score: number;
  reasoning: string[];
  boundary_concerns: Array<{
    boundary: string;
    violated: boolean;
    severity: number;
    recommendation: string;
  }>;
  created_at: string;
  timeout_at: string;
}

interface HILTApprovalPanelProps {
  personaId?: string;
  onApprovalSubmit: (taskId: string, action: string, data: any) => void;
}

const HILTApprovalPanel: React.FC<HILTApprovalPanelProps> = ({
  personaId,
  onApprovalSubmit
}) => {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
  const [modifiedDecision, setModifiedDecision] = useState('');
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchPendingApprovals();
    const interval = setInterval(fetchPendingApprovals, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, [personaId]);

  const fetchPendingApprovals = async () => {
    try {
      const params = personaId ? `?persona_id=${personaId}` : '';
      const response = await fetch(`/api/v1/hilt/approvals/pending${params}`);
      const data = await response.json();
      setApprovals(data);
    } catch (error) {
      console.error('Failed to fetch approvals:', error);
    }
  };

  const handleApproval = async (action: string) => {
    if (!selectedApproval) return;

    setLoading(true);
    try {
      await onApprovalSubmit(selectedApproval.task_id, action, {
        modified_decision: action === 'MODIFY' ? modifiedDecision : null,
        feedback: feedback || null,
        delegate_to: null
      });

      // Remove from list
      setApprovals(prev => prev.filter(a => a.task_id !== selectedApproval.task_id));
      setSelectedApproval(null);
      setModifiedDecision('');
      setFeedback('');
    } catch (error) {
      console.error('Failed to submit approval:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTimeRemaining = (timeout: string) => {
    const remaining = new Date(timeout).getTime() - new Date().getTime();
    if (remaining <= 0) return 'Expired';
    
    const minutes = Math.floor(remaining / 60000);
    const seconds = Math.floor((remaining % 60000) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getRiskColor = (risk: number) => {
    if (risk >= 0.7) return 'text-red-600';
    if (risk >= 0.4) return 'text-yellow-600';
    return 'text-green-600';
  };

  return (
    <div className="bg-white rounded-lg shadow-lg">
      <div className="p-6 border-b">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">HILT Approval Queue</h2>
          <div className="flex items-center space-x-2">
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
              {approvals.length} Pending
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 divide-x">
        {/* Approval List */}
        <div className="lg:col-span-1 p-4 max-h-96 overflow-y-auto">
          {approvals.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No pending approvals
            </div>
          ) : (
            <div className="space-y-2">
              {approvals.map(approval => (
                <div
                  key={approval.task_id}
                  onClick={() => setSelectedApproval(approval)}
                  className={`p-3 rounded cursor-pointer transition ${
                    selectedApproval?.task_id === approval.task_id
                      ? 'bg-blue-50 border-blue-500 border'
                      : 'bg-gray-50 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {approval.task_description}
                    </span>
                    <span className="text-xs text-gray-500 flex items-center">
                      <Clock className="w-3 h-3 mr-1" />
                      {getTimeRemaining(approval.timeout_at)}
                    </span>
                  </div>
                  
                  <div className="flex space-x-4 text-xs">
                    <span className={`flex items-center ${getConfidenceColor(approval.confidence)}`}>
                      <BarChart className="w-3 h-3 mr-1" />
                      {(approval.confidence * 100).toFixed(0)}%
                    </span>
                    <span className={`flex items-center ${getRiskColor(approval.risk_score)}`}>
                      <AlertTriangle className="w-3 h-3 mr-1" />
                      Risk: {(approval.risk_score * 100).toFixed(0)}%
                    </span>
                  </div>

                  {approval.boundary_concerns.length > 0 && (
                    <div className="mt-1">
                      <span className="text-xs text-red-600">
                        {approval.boundary_concerns.filter(b => b.violated).length} boundary violations
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Approval Details */}
        <div className="lg:col-span-2 p-6">
          {selectedApproval ? (
            <div className="space-y-4">
              {/* Task Info */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Task Details
                </h3>
                <p className="text-gray-700">{selectedApproval.task_description}</p>
                <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Confidence:</span>
                    <span className={`ml-2 font-medium ${getConfidenceColor(selectedApproval.confidence)}`}>
                      {(selectedApproval.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Risk Score:</span>
                    <span className={`ml-2 font-medium ${getRiskColor(selectedApproval.risk_score)}`}>
                      {(selectedApproval.risk_score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Decision */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-1">Proposed Decision</h4>
                <div className="p-3 bg-blue-50 rounded text-sm text-blue-900">
                  {selectedApproval.decision}
                </div>
              </div>

              {/* Reasoning */}
              <div>
                <h4 className="font-semibold text-gray-900 mb-1">Reasoning</h4>
                <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                  {selectedApproval.reasoning.map((reason, i) => (
                    <li key={i}>{reason}</li>
                  ))}
                </ul>
              </div>

              {/* Boundary Concerns */}
              {selectedApproval.boundary_concerns.length > 0 && (
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Boundary Concerns</h4>
                  <div className="space-y-2">
                    {selectedApproval.boundary_concerns.map((concern, i) => (
                      <div
                        key={i}
                        className={`p-2 rounded text-sm ${
                          concern.violated ? 'bg-red-50 text-red-900' : 'bg-yellow-50 text-yellow-900'
                        }`}
                      >
                        <div className="flex justify-between">
                          <span className="font-medium">
                            {concern.violated ? 'Violation' : 'Near Boundary'}
                          </span>
                          <span>Severity: {(concern.severity * 100).toFixed(0)}%</span>
                        </div>
                        <p className="mt-1">{concern.recommendation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Modification Field */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Modified Decision (Optional)
                </label>
                <textarea
                  value={modifiedDecision}
                  onChange={(e) => setModifiedDecision(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md text-sm"
                  rows={3}
                  placeholder="Enter modified decision if changes are needed..."
                />
              </div>

              {/* Feedback Field */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Feedback
                </label>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md text-sm"
                  rows={2}
                  placeholder="Provide feedback for learning..."
                />
              </div>

              {/* Action Buttons */}
              <div className="flex space-x-3 pt-4">
                <button
                  onClick={() => handleApproval('APPROVE')}
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center justify-center"
                >
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Approve
                </button>
                
                <button
                  onClick={() => handleApproval('MODIFY')}
                  disabled={loading || !modifiedDecision}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center"
                >
                  <Edit className="w-4 h-4 mr-2" />
                  Modify
                </button>
                
                <button
                  onClick={() => handleApproval('REJECT')}
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 flex items-center justify-center"
                >
                  <XCircle className="w-4 h-4 mr-2" />
                  Reject
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              Select an approval request to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HILTApprovalPanel;