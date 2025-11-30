import { useState } from 'react';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async () => {
    if(!input) return;
    
    const newMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, newMsg]);
    setIsLoading(true);
    const currentInput = input;
    setInput('');

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: currentInput })
      });
      
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'bot', content: data.reply }]);
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: 'bot', content: "Sorry, connection error." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] w-full max-w-2xl bg-white shadow-xl rounded-lg overflow-hidden border">
      <div className="bg-indigo-600 p-4">
        <h1 className="text-white font-bold text-lg">IndoFund AI Advisor</h1>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
             <div className={`max-w-[80%] p-3 rounded-lg text-sm ${
               m.role === 'user' 
               ? 'bg-indigo-600 text-white rounded-br-none' 
               : 'bg-white border text-gray-800 rounded-bl-none shadow-sm'
             }`}>
               {/* Use a Markdown renderer in production, text for now */}
               <p className="whitespace-pre-wrap">{m.content}</p>
             </div>
          </div>
        ))}
        {isLoading && <div className="text-gray-400 text-sm italic">Thinking...</div>}
      </div>

      <div className="p-4 bg-white border-t flex gap-2">
        <input 
          className="flex-1 border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="Ask for 'Top Saham Funds' or 'Why is Fund X good?'"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
        />
        <button 
          onClick={sendMessage}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-md font-medium transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}