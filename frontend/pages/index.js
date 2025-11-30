import { useState } from 'react';

// --- 1. ADD HELPER FUNCTION HERE (Outside the component) ---
const getPartnerLink = (fundName) => {
  // 1. CLEAN THE NAME: Remove special chars for URL safety
  // If the fundName is just a placeholder, the search will still work but be generic
  const query = encodeURIComponent(fundName);
  
  // OPTION A: Search Link (Directs to Bibit search)
  return `https://www.bibit.id/reksadana/search?q=${query}&ref=sxlphey`;
};

export default function Home() {
  const [input, setInput] = useState('');
  const [chat, setChat] = useState([]);
  const [loading, setLoading] = useState(false);

  const sendMsg = async () => {
    if (!input) return;
    const newMsg = { role: 'user', content: input };
    setChat([...chat, newMsg]);
    setLoading(true);
    setInput('');

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: input, history: chat })
      });
      const data = await res.json();
      
      setChat(prev => [...prev, { role: 'agent', content: data.reply }]);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center p-4">
      <div className="w-full max-w-2xl bg-white shadow-lg rounded-lg overflow-hidden">
        <div className="bg-blue-600 p-4 text-white font-bold">
          IndoFund AI Advisor
        </div>
        
        <div className="h-96 overflow-y-auto p-4 space-y-4">
          {chat.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-xs md:max-w-md p-3 rounded-lg ${
                msg.role === 'user' ? 'bg-blue-100 text-blue-900' : 'bg-gray-100 text-gray-900'
              }`}>
                {/* Render Text */}
                <p className="whitespace-pre-wrap">{msg.content}</p>
                
                {/* --- 2. UPDATE REFERRAL UI HERE --- */}
                {/* Only show this if the agent mentions a "Score" (indicating a recommendation) */}
                {msg.role === 'agent' && msg.content.includes("Score") && ( 
                  <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-800 font-semibold mb-2">
                      🚀 Ready to invest in this fund?
                    </p>
                    
                    {/* Note: Currently passing a placeholder. 
                        To make this dynamic, we need to extract the specific fund name 
                        from the 'msg.content' or have the backend send it separately. */}
                    <a 
                      href={getPartnerLink("Reksadana Saham")} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="inline-block bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded transition-colors text-sm"
                    >
                      Buy on Bibit.id
                    </a>
                    
                    <div className="text-xs text-gray-500 mt-1">
                      *Redirects to our trusted banking partner.
                    </div>
                  </div>
                )}
                {/* ---------------------------------- */}

              </div>
            </div>
          ))}
          {loading && <div className="text-gray-400 text-sm">AI is thinking...</div>}
        </div>

        <div className="p-4 border-t flex gap-2">
          <input 
            className="flex-1 border rounded p-2"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMsg()}
            placeholder="Ask for top Saham funds or why Sucorinvest is good..."
          />
          <button onClick={sendMsg} className="bg-blue-600 text-white px-4 rounded hover:bg-blue-700">
            Send
          </button>
        </div>
      </div>
    </div>
  );
}