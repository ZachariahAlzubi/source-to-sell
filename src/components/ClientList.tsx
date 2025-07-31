import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Plus, Building2, ExternalLink, MessageSquare } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/components/ui/use-toast';
import { ClientForm } from './ClientForm';
import { ClientChat } from './ClientChat';

interface Account {
  id: string;
  name: string;
  domain?: string;
  website?: string;
  industry?: string;
  size_hint?: string;
  summary?: string;
  created_at: string;
}

interface ClientListProps {
  productId: string;
}

export const ClientList: React.FC<ClientListProps> = ({ productId }) => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [showClientForm, setShowClientForm] = useState(false);
  const [selectedClient, setSelectedClient] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    fetchAccounts();
  }, [productId]);

  const fetchAccounts = async () => {
    try {
      const { data, error } = await supabase
        .from('accounts')
        .select('*')
        .eq('product_id', productId)
        .order('created_at', { ascending: false });

      if (error) throw error;
      setAccounts(data || []);
    } catch (error) {
      console.error('Error fetching accounts:', error);
      toast({
        title: "Error",
        description: "Failed to load clients",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClientCreated = () => {
    setShowClientForm(false);
    fetchAccounts();
    toast({
      title: "Success",
      description: "Client added successfully",
    });
  };

  if (loading) {
    return <div className="text-muted-foreground">Loading clients...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h4 className="text-sm font-medium text-muted-foreground">
          {accounts.length} client{accounts.length !== 1 ? 's' : ''}
        </h4>
        <Button size="sm" onClick={() => setShowClientForm(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Add Client
        </Button>
      </div>

      {accounts.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Building2 className="mx-auto h-8 w-8 mb-2" />
          <p>No clients added for this product yet</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {accounts.map((account) => (
            <Card key={account.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-primary" />
                      {account.name}
                      {account.website && (
                        <a
                          href={account.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-muted-foreground hover:text-primary"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </CardTitle>
                    {account.domain && (
                      <p className="text-sm text-muted-foreground">{account.domain}</p>
                    )}
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setSelectedClient(account)}
                    className="gap-2"
                  >
                    <MessageSquare className="h-4 w-4" />
                    Chat
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex flex-wrap gap-2 mb-3">
                  {account.industry && (
                    <Badge variant="secondary">{account.industry}</Badge>
                  )}
                  {account.size_hint && (
                    <Badge variant="outline">{account.size_hint}</Badge>
                  )}
                </div>
                {account.summary && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {account.summary}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showClientForm && (
        <ClientForm
          open={showClientForm}
          productId={productId}
          onClose={() => setShowClientForm(false)}
          onSuccess={handleClientCreated}
        />
      )}

      {selectedClient && (
        <ClientChat
          open={!!selectedClient}
          client={selectedClient}
          onClose={() => setSelectedClient(null)}
        />
      )}
    </div>
  );
};