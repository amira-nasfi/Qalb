import React, { useState, useEffect } from "react";
import { Users, UserPlus, ShieldAlert, CheckCircle } from "lucide-react";
import { getUsers, toggleUserSuspend } from "../../api/admin";
import type { UserItem } from "../../api/admin";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import { InviteModal } from "./InviteModal";

export const UserManagementPage: React.FC = () => {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const data = await getUsers();
      setUsers(data);
    } catch (err) {
      console.error("Failed to load users", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleToggleSuspend = async (userId: number) => {
    try {
      const res = await toggleUserSuspend(userId);
      setUsers(users.map(u => u.id === userId ? { ...u, is_suspended: res.is_suspended } : u));
    } catch (err) {
      console.error("Failed to toggle suspend status", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-navy-dark flex items-center gap-2">
            <Users size={28} className="text-mint" />
            User Management
          </h1>
          <p className="text-tertiary">Manage personnel access and roles.</p>
        </div>
        <Button onClick={() => setIsInviteModalOpen(true)}>
          <UserPlus size={16} className="mr-2" /> Invite User
        </Button>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="p-4 text-sm font-semibold text-secondary">Name</th>
                <th className="p-4 text-sm font-semibold text-secondary">Role</th>
                <th className="p-4 text-sm font-semibold text-secondary">Organization</th>
                <th className="p-4 text-sm font-semibold text-secondary">Status</th>
                <th className="p-4 text-sm font-semibold text-secondary text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={5} className="p-4 text-center">Loading...</td></tr>
              ) : users.map(user => (
                <tr key={user.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="p-4">
                    <div className="font-medium text-navy-dark">{user.full_name || user.username}</div>
                    <div className="text-xs text-tertiary">{user.email}</div>
                  </td>
                  <td className="p-4">
                    <Badge variant={user.role === 'ADMIN' ? 'critical' : user.role === 'PHYSICIAN' ? 'default' : 'secondary'}>
                      {user.role}
                    </Badge>
                  </td>
                  <td className="p-4 text-sm text-secondary">{user.organization || '-'}</td>
                  <td className="p-4">
                    {user.is_suspended ? (
                      <span className="flex items-center text-critical text-sm"><ShieldAlert size={14} className="mr-1" /> Suspended</span>
                    ) : (
                      <span className="flex items-center text-success text-sm"><CheckCircle size={14} className="mr-1" /> Active</span>
                    )}
                  </td>
                  <td className="p-4 text-right space-x-2">
                    <Button 
                      variant="secondary" 
                      size="sm"
                      onClick={() => handleToggleSuspend(user.id)}
                    >
                      {user.is_suspended ? 'Reinstate' : 'Suspend'}
                    </Button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && !isLoading && (
                <tr><td colSpan={5} className="p-4 text-center text-tertiary">No users found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {isInviteModalOpen && (
        <InviteModal 
          onClose={() => setIsInviteModalOpen(false)} 
          onSuccess={() => {
            setIsInviteModalOpen(false);
            fetchUsers();
          }} 
        />
      )}
    </div>
  );
};
