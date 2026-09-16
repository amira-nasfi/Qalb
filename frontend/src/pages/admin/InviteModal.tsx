import React, { useState } from "react";
import { inviteUser } from "../../api/admin";
import { Button } from "../../components/ui/Button";

interface InviteModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export const InviteModal: React.FC<InviteModalProps> = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    role: "FIELD_AGENT",
    organization: "",
    password: "", // Temporary password for MVP
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      await inviteUser(formData);
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || JSON.stringify(err.response?.data) || "Failed to invite user");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-xl font-bold text-navy-dark mb-4">Invite New User</h2>
        {error && <div className="mb-4 text-critical text-sm">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">First Name</label>
              <input type="text" className="w-full border rounded p-2" required
                value={formData.first_name} onChange={e => setFormData({...formData, first_name: e.target.value})} />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Last Name</label>
              <input type="text" className="w-full border rounded p-2" required
                value={formData.last_name} onChange={e => setFormData({...formData, last_name: e.target.value})} />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input type="text" className="w-full border rounded p-2" required
              value={formData.username} onChange={e => setFormData({...formData, username: e.target.value})} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input type="email" className="w-full border rounded p-2" required
              value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Role</label>
            <select className="w-full border rounded p-2" required
              value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})}>
              <option value="FIELD_AGENT">Field Agent</option>
              <option value="PHYSICIAN">Physician</option>
              <option value="ADMIN">Administrator</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Organization</label>
            <input type="text" className="w-full border rounded p-2"
              value={formData.organization} onChange={e => setFormData({...formData, organization: e.target.value})} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Temporary Password</label>
            <input type="password" className="w-full border rounded p-2" required
              value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} />
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <Button variant="secondary" onClick={onClose} type="button">Cancel</Button>
            <Button type="submit" isLoading={isLoading}>Send Invite</Button>
          </div>
        </form>
      </div>
    </div>
  );
};
