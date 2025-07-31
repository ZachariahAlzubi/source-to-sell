import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

interface ChatRequest {
  message: string;
  apiKey?: string;
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { message, apiKey }: ChatRequest = await req.json();

    // Use provided API key or fall back to environment variable
    const openAIApiKey = apiKey || Deno.env.get('OPENAI_API_KEY');
    
    if (!openAIApiKey) {
      throw new Error('OpenAI API key is required');
    }

    // First, search for relevant information about the topic
    const searchResponse = await fetch('https://api.perplexity.ai/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${Deno.env.get('PERPLEXITY_API_KEY') || 'pplx-YOUR_KEY_HERE'}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'llama-3.1-sonar-large-128k-online',
        messages: [
          {
            role: 'system',
            content: 'You are a helpful research assistant. Provide current, accurate information about companies, markets, and business insights. Be concise and factual.'
          },
          {
            role: 'user',
            content: `Research current information about this topic and provide relevant business insights: ${message}`
          }
        ],
        temperature: 0.2,
        top_p: 0.9,
        max_tokens: 1000,
        return_images: false,
        return_related_questions: false,
        search_recency_filter: 'month',
        frequency_penalty: 1,
        presence_penalty: 0
      }),
    });

    let researchData = '';
    if (searchResponse.ok) {
      const searchData = await searchResponse.json();
      researchData = searchData.choices?.[0]?.message?.content || '';
    }

    // Now use OpenAI to provide intelligent analysis
    const systemPrompt = `You are an expert CRM and sales assistant with access to current market data. Your role is to help with:

1. Company research and analysis
2. Market insights and trends
3. Sales strategy recommendations
4. Competitive analysis
5. Lead qualification advice
6. Pitch and proposal guidance

Use the following current research data to enhance your responses:
${researchData ? `\n--- Current Research Data ---\n${researchData}\n--- End Research Data ---\n` : ''}

Provide actionable insights and practical recommendations. Be conversational but professional.`;

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${openAIApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-4.1-2025-04-14',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: message }
        ],
        temperature: 0.7,
        max_tokens: 1500,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`OpenAI API error: ${errorData.error?.message || 'Unknown error'}`);
    }

    const data = await response.json();
    const aiResponse = data.choices[0].message.content;

    return new Response(JSON.stringify({ 
      response: aiResponse,
      hasResearchData: !!researchData 
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error in intelligent-chat function:', error);
    
    let errorMessage = 'An error occurred while processing your request.';
    
    if (error.message?.includes('API key')) {
      errorMessage = 'OpenAI API key is required. Please provide your API key to use the chat feature.';
    } else if (error.message?.includes('OpenAI API error')) {
      errorMessage = error.message;
    }

    return new Response(JSON.stringify({ 
      error: errorMessage,
      needsApiKey: error.message?.includes('API key')
    }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});