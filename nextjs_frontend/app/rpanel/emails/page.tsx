"use client";

import React, { useEffect, useState } from "react";
import { Mail, Plus, Trash2 } from "lucide-react";
import { getEmailAccounts, createEmailAccount, deleteEmailAccount } from "@/app/actions/handson/rpanel/manage-email";
import { getClientWebsites } from "@/app/actions/handson/rpanel/get-client-websites";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RPanelNav } from "@/components/custom/nav/rpanel-nav";

export default function EmailsPage() {
  const [emails, setEmails] = useState<any[]>([]);
  const [websites, setWebsites] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);

  // Create Form State
  const [newEmailUser, setNewEmailUser] = useState("");
  const [newEmailPass, setNewEmailPass] = useState("");
  const [selectedWebsite, setSelectedWebsite] = useState("");

  const fetchData = async () => {
    setIsLoading(true);
    // Fetch Emails
    const emailRes = await getEmailAccounts("");
    if (emailRes.success) {
      setEmails(emailRes.data);
    }
    // Fetch Websites for dropdown
    const siteRes = await getClientWebsites();
    if (siteRes.message?.success) {
        setWebsites(siteRes.message.websites);
        if (siteRes.message.websites.length > 0 && !selectedWebsite) {
            setSelectedWebsite(siteRes.message.websites[0].name);
        }
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchData();
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
          fetchData();
      } else {
          alert("Failed: " + res.error);
      }
      setIsCreating(false);
  };

  const handleDelete = async (websiteName: string, emailUser: string) => {
      if (confirm(`Delete ${emailUser}?`)) {
          await deleteEmailAccount(websiteName, emailUser);
          fetchData();
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
                    <div>
                        <label className="text-sm font-medium">Website</label>
                        <Select value={selectedWebsite} onValueChange={setSelectedWebsite}>
                            <SelectTrigger>
                                <SelectValue placeholder="Select website" />
                            </SelectTrigger>
                            <SelectContent>
                                {websites.map((site) => (
                                    <SelectItem key={site.name} value={site.name}>
                                        {site.domain}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div>
                        <label className="text-sm font-medium">Username</label>
                        <Input placeholder="e.g. info" value={newEmailUser} onChange={e => setNewEmailUser(e.target.value)} />
                    </div>
                    <div>
                        <label className="text-sm font-medium">Password</label>
                        <Input type="password" placeholder="Password" value={newEmailPass} onChange={e => setNewEmailPass(e.target.value)} />
                    </div>
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
