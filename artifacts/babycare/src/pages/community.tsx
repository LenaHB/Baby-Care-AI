import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { Users, Heart, MessageCircle, Plus, BadgeCheck } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useGetCommunityFeed, useCreatePost, useLikePost, useGetPostComments, useAddComment } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

const CATEGORIES = ["general", "feeding", "sleep", "health", "development", "emotional_support", "milestones"];

const postSchema = z.object({
  author_name: z.string().min(1),
  title: z.string().optional(),
  content: z.string().min(5),
  category: z.enum(["general", "feeding", "sleep", "health", "development", "emotional_support", "milestones"])
});

const commentSchema = z.object({
  author_name: z.string().min(1),
  content: z.string().min(1)
});

export default function Community() {
  const [activeTab, setActiveTab] = useState<string>("general");
  const [isPostModalOpen, setIsPostModalOpen] = useState(false);
  const [selectedPostId, setSelectedPostId] = useState<number | null>(null);
  
  const queryClient = useQueryClient();
  const feedQuery = useGetCommunityFeed({ category: activeTab });
  const likeMut = useLikePost({ onSuccess: () => queryClient.invalidateQueries({ queryKey: ["/api/community/feed"] }) });
  
  const createMut = useCreatePost({ 
    onSuccess: () => { 
      queryClient.invalidateQueries({ queryKey: ["/api/community/feed"] }); 
      setIsPostModalOpen(false); 
    } 
  });

  const { register: registerPost, handleSubmit: handlePostSubmit, reset: resetPost } = useForm<z.infer<typeof postSchema>>({
    resolver: zodResolver(postSchema),
    defaultValues: { category: "general" }
  });

  const onPostSubmit = (data: z.infer<typeof postSchema>) => {
    createMut.mutate({ data: { ...data, title: data.title || null } });
    resetPost();
  };

  return (
    <div className="p-6 md:p-10 max-w-5xl mx-auto pb-20">
      <header className="mb-10 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-pink-100 rounded-2xl">
            <Users className="w-8 h-8 text-pink-600" />
          </div>
          <div>
            <h1 className="text-4xl font-display font-bold text-foreground">Mothers Community</h1>
            <p className="text-lg text-muted-foreground">Share experiences, ask questions, find support.</p>
          </div>
        </div>
        <button
          onClick={() => setIsPostModalOpen(true)}
          className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-pink-400 to-rose-400 text-white rounded-xl font-bold shadow-lg shadow-pink-500/25 hover:shadow-xl hover:-translate-y-0.5 transition-all whitespace-nowrap"
        >
          <Plus className="w-5 h-5" />
          New Post
        </button>
      </header>

      <div className="flex overflow-x-auto gap-2 pb-4 mb-6 hide-scrollbar">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setActiveTab(cat)}
            className={`
              px-5 py-2.5 rounded-full font-bold capitalize whitespace-nowrap transition-all
              ${activeTab === cat 
                ? 'bg-foreground text-background shadow-md' 
                : 'bg-white border border-border text-muted-foreground hover:bg-muted'
              }
            `}
          >
            {cat.replace('_', ' ')}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
        <div className="md:col-span-8 space-y-6">
          {feedQuery.isLoading && <div className="text-center py-10"><div className="w-8 h-8 border-4 border-pink-400 border-t-transparent rounded-full animate-spin mx-auto"></div></div>}
          
          {feedQuery.data?.length === 0 && (
            <div className="text-center py-20 bg-white rounded-3xl border border-border">
              <Users className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
              <p className="text-muted-foreground font-medium">No posts in this category yet. Be the first!</p>
            </div>
          )}

          {feedQuery.data?.map(post => (
            <div key={post.id} className="bg-white rounded-3xl p-6 shadow-sm border border-border hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary/40 to-secondary/40 flex items-center justify-center font-bold text-foreground">
                    {post.author_name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-foreground">{post.author_name}</span>
                      {post.is_verified && <BadgeCheck className="w-4 h-4 text-blue-500" />}
                    </div>
                    <span className="text-xs text-muted-foreground">{formatDistanceToNow(new Date(post.created_at))} ago</span>
                  </div>
                </div>
                <span className="text-xs font-bold px-3 py-1 bg-muted rounded-full text-muted-foreground capitalize">
                  {post.category.replace('_', ' ')}
                </span>
              </div>
              
              {post.title && <h3 className="text-xl font-bold mb-2">{post.title}</h3>}
              <p className="text-foreground/90 whitespace-pre-wrap mb-6">{post.content}</p>
              
              <div className="flex items-center gap-6 border-t pt-4">
                <button 
                  onClick={() => likeMut.mutate({ data: { post_id: post.id } })}
                  className="flex items-center gap-2 text-muted-foreground hover:text-pink-500 font-medium transition-colors"
                >
                  <Heart className={`w-5 h-5 ${post.likes > 0 ? 'fill-pink-500 text-pink-500' : ''}`} />
                  {post.likes}
                </button>
                <button 
                  onClick={() => setSelectedPostId(post.id === selectedPostId ? null : post.id)}
                  className="flex items-center gap-2 text-muted-foreground hover:text-blue-500 font-medium transition-colors"
                >
                  <MessageCircle className="w-5 h-5" />
                  {post.comment_count}
                </button>
              </div>

              {selectedPostId === post.id && (
                <CommentsSection postId={post.id} />
              )}
            </div>
          ))}
        </div>

        <div className="hidden md:block md:col-span-4">
          <div className="bg-gradient-to-br from-primary/20 to-secondary/20 rounded-3xl p-6 sticky top-6 border border-white">
            <h3 className="font-display font-bold text-xl mb-2">Community Guidelines</h3>
            <ul className="space-y-3 text-sm text-foreground/80 font-medium">
              <li>✨ Be supportive and kind</li>
              <li>🩺 No medical diagnosing (always consult a doctor)</li>
              <li>💖 Respect different parenting styles</li>
              <li>🚫 No spam or promotions</li>
            </ul>
            <img src={`${import.meta.env.BASE_URL}images/baby-hero.png`} className="w-full mt-6 opacity-80 mix-blend-multiply" alt="Community illustration" />
          </div>
        </div>
      </div>

      {isPostModalOpen && (
        <div className="fixed inset-0 bg-foreground/20 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl p-8 w-full max-w-lg shadow-2xl animate-in fade-in zoom-in-95">
            <h2 className="text-2xl font-display font-bold mb-6">Create Post</h2>
            <form onSubmit={handlePostSubmit(onPostSubmit)} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold mb-1">Your Name</label>
                  <input {...registerPost("author_name")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-pink-400 outline-none" required />
                </div>
                <div>
                  <label className="block text-sm font-bold mb-1">Category</label>
                  <select {...registerPost("category")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-pink-400 outline-none bg-white">
                    {CATEGORIES.map(c => <option key={c} value={c}>{c.replace('_', ' ')}</option>)}
                  </select>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-bold mb-1">Title (Optional)</label>
                <input {...registerPost("title")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-pink-400 outline-none" placeholder="What's on your mind?" />
              </div>

              <div>
                <label className="block text-sm font-bold mb-1">Message</label>
                <textarea {...registerPost("content")} className="w-full px-4 py-3 rounded-xl border-2 border-border focus:border-pink-400 outline-none min-h-32" required placeholder="Share your experience or ask a question..." />
              </div>

              <div className="flex gap-3 pt-4">
                <button type="button" onClick={() => setIsPostModalOpen(false)} className="flex-1 py-3 bg-muted text-muted-foreground rounded-xl font-bold hover:bg-muted/80">Cancel</button>
                <button type="submit" disabled={createMut.isPending} className="flex-1 py-3 bg-pink-500 text-white rounded-xl font-bold shadow-lg shadow-pink-500/25">Post</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function CommentsSection({ postId }: { postId: number }) {
  const queryClient = useQueryClient();
  const commentsQuery = useGetPostComments(postId);
  const commentMut = useAddComment({
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/community/comments/${postId}`] });
      queryClient.invalidateQueries({ queryKey: ["/api/community/feed"] }); // updates comment count
    }
  });

  const { register, handleSubmit, reset } = useForm<z.infer<typeof commentSchema>>({
    resolver: zodResolver(commentSchema)
  });

  const onSubmit = (data: z.infer<typeof commentSchema>) => {
    commentMut.mutate({ data: { post_id: postId, ...data } });
    reset();
  };

  return (
    <div className="mt-6 pt-6 border-t border-border animate-in slide-in-from-top-2">
      <div className="space-y-4 mb-6">
        {commentsQuery.isLoading && <div className="text-sm text-muted-foreground">Loading comments...</div>}
        {commentsQuery.data?.map(c => (
          <div key={c.id} className="bg-muted/30 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-sm text-foreground">{c.author_name}</span>
              <span className="text-xs text-muted-foreground">{formatDistanceToNow(new Date(c.created_at))} ago</span>
            </div>
            <p className="text-sm text-foreground/80">{c.content}</p>
          </div>
        ))}
        {commentsQuery.data?.length === 0 && <p className="text-sm text-muted-foreground text-center">No comments yet.</p>}
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="flex items-start gap-3">
        <input {...register("author_name")} placeholder="Name" className="w-1/4 px-4 py-2 rounded-xl border border-border text-sm outline-none focus:border-pink-400" required />
        <input {...register("content")} placeholder="Add a comment..." className="flex-1 px-4 py-2 rounded-xl border border-border text-sm outline-none focus:border-pink-400" required />
        <button type="submit" disabled={commentMut.isPending} className="px-4 py-2 bg-foreground text-background rounded-xl font-bold text-sm shrink-0">Post</button>
      </form>
    </div>
  );
}
