import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Plus, Package, Users } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/components/ui/use-toast';
import { ProductForm } from './ProductForm';
import { ClientList } from './ClientList';
import { Badge } from '@/components/ui/badge';

interface Product {
  id: string;
  name: string;
  description?: string;
  price?: number;
  category?: string;
  created_at: string;
}

export const ProductTabs = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [activeTab, setActiveTab] = useState<string>('');
  const [showProductForm, setShowProductForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const { data, error } = await supabase
        .from('products')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      
      setProducts(data || []);
      if (data && data.length > 0 && !activeTab) {
        setActiveTab(data[0].id);
      }
    } catch (error) {
      console.error('Error fetching products:', error);
      toast({
        title: "Error",
        description: "Failed to load products",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleProductCreated = () => {
    setShowProductForm(false);
    fetchProducts();
    toast({
      title: "Success",
      description: "Product created successfully",
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading products...</div>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="text-center py-12">
        <Package className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-medium mb-2">No products yet</h3>
        <p className="text-muted-foreground mb-6">Create your first product to start managing clients</p>
        <Button onClick={() => setShowProductForm(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Create Product
        </Button>
        {showProductForm && (
          <ProductForm 
            open={showProductForm}
            onClose={() => setShowProductForm(false)}
            onSuccess={handleProductCreated}
          />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">CRM Dashboard</h1>
          <p className="text-muted-foreground">Manage your products and clients</p>
        </div>
        <Button onClick={() => setShowProductForm(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          New Product
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-auto gap-1 h-auto p-1 bg-muted">
          {products.map((product) => (
            <TabsTrigger 
              key={product.id} 
              value={product.id}
              className="flex items-center gap-2 px-4 py-3 whitespace-nowrap data-[state=active]:bg-background data-[state=active]:text-foreground"
            >
              <Package className="h-4 w-4" />
              <span>{product.name}</span>
              {product.category && (
                <Badge variant="secondary" className="text-xs">
                  {product.category}
                </Badge>
              )}
            </TabsTrigger>
          ))}
        </TabsList>

        {products.map((product) => (
          <TabsContent key={product.id} value={product.id} className="mt-6">
            <div className="space-y-6">
              <div className="border rounded-lg p-6 bg-card">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-2xl font-bold mb-2">{product.name}</h2>
                    {product.description && (
                      <p className="text-muted-foreground">{product.description}</p>
                    )}
                  </div>
                  <div className="text-right">
                    {product.price && (
                      <div className="text-2xl font-bold text-primary">
                        ${product.price.toLocaleString()}
                      </div>
                    )}
                    {product.category && (
                      <Badge variant="outline" className="mt-2">
                        {product.category}
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              <div className="border rounded-lg p-6 bg-card">
                <div className="flex items-center gap-2 mb-4">
                  <Users className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-semibold">Clients & Prospects</h3>
                </div>
                <ClientList productId={product.id} />
              </div>
            </div>
          </TabsContent>
        ))}
      </Tabs>

      {showProductForm && (
        <ProductForm 
          open={showProductForm}
          onClose={() => setShowProductForm(false)}
          onSuccess={handleProductCreated}
        />
      )}
    </div>
  );
};