"use client";

import React, { useEffect, useState } from "react";
import { Mail, Plus, Trash2 } from "lucide-react";
import { getEmailAccounts, createEmailAccount, deleteEmailAccount } from "@/app/actions/handson/rpanel/manage-email";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter
} from "@/components/ui/dialog";
import { RPanelNav } from "@/components/custom/nav/rpanel-nav";

export default function EmailsPage() {
  const [emails, setEmails] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  // Create Form State
  const [newEmailUser, setNewEmailUser] = useState("");
  const [newEmailPass, setNewEmailPass] = useState("");
  const [selectedWebsite, setSelectedWebsite] = useState(""); // Needs logic to pick website

  const fetchEmails = async () => {
    setIsLoading(true);
    const res = await getEmailAccounts(""); // Backend needs to infer client
    if (res.success) {
      setEmails(res.data);
      if (res.data.length > 0) setSelectedWebsite(res.data[0].website_name);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchEmails();
  }, []);

  const handleCreate = async () => {
      if (!newEmailUser || !newEmailPass || !selectedWebsite) return;
      setIsCreating(true);
      const res = await createEmailAccount(selectedWebsite, {
          email_user: newEmailUser,
          password: newEmailPass,
          quota_mb: 1024
      });
      if (res.success) {
          setNewEmailUser("");
          setNewEmailPass("");
          fetchEmails();
      } else {
          alert("Failed: " + res.error);
      }
      setIsCreating(false);
  };

  const handleDelete = async (websiteName: string, emailUser: string) => {
      if (confirm(`Delete ${emailUser}?`)) {
          await deleteEmailAccount(websiteName, emailUser);
          fetchEmails();
      }
  };

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <RPanelNav />
      <main className="flex-1 p-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Email Accounts</h1>

          <Dialog>
            <DialogTrigger asChild>
                <Button><Plus className="mr-2 h-4 w-4" /> New Account</Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader><DialogTitle>Create Email Account</DialogTitle></DialogHeader>
                <div className="space-y-4 py-4">
                    <Input placeholder="Username (e.g. info)" value={newEmailUser} onChange={e => setNewEmailUser(e.target.value)} />
                    <Input type="password" placeholder="Password" value={newEmailPass} onChange={e => setNewEmailPass(e.target.value)} />
                    {/* Website selection would go here */}
                </div>
                <DialogFooter>
                    <Button onClick={handleCreate} disabled={isCreating}>Create</Button>
                </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm text-left">
              <thead className="bg-muted/50 text-muted-foreground font-medium">
                <tr>
                  <th className="px-6 py-4">Email Address</th>
                  <th className="px-6 py-4">Domain</th>
                  <th className="px-6 py-4">Quota</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {emails.map((acc, i) => (
                  <tr key={i} className="hover:bg-muted/50">
                    <td className="px-6 py-4 font-medium">{acc.email_user}@{acc.domain}</td>
                    <td className="px-6 py-4">{acc.domain}</td>
                    <td className="px-6 py-4">{acc.quota_mb} MB</td>
                    <td className="px-6 py-4 text-right">
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(acc.website_name, acc.email_user)}>
                            <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
