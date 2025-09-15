from __future__ import annotations
from .state import start_state, AgentState
from .guards import score_state
from .plan_execute import plan_once, execute_once

class LoopConfig:
    def __init__(self, max_steps=10, critic_threshold=0.72):
        self.max_steps = max_steps
        self.critic_threshold = critic_threshold

def run(llm, user_goal: str, cfg: LoopConfig, base_params: dict) -> AgentState:
    state = start_state(user_goal)
    print(f"Starting research on: {user_goal}")
    
    for step in range(cfg.max_steps):
        print(f"\n--- Step {step + 1}/{cfg.max_steps} ---")
        
        try:
            plan_state = plan_once(llm, state, base_params)
            print(f"Plan: {plan_state.plan[:3]}...")  # Show first 3 plan items
            
            cand = execute_once(llm, plan_state, base_params)
            print(f"Found {len(cand.facts)} facts")
            
            s = score_state(state, cand)
            print(f"Score: {s:.3f} (threshold: {cfg.critic_threshold})")
            
            if s < cfg.critic_threshold:
                print("Score too low, continuing...")
                continue
                
            state = AgentState(
                facts=cand.facts, goals=state.goals, plan=[],
                constraints=state.constraints, step=cand.step
            )
            
            print(f"Updated state: {len(state.facts)} total facts")
            
            if not state.goals or len(state.facts) >= 20:
                print("Stopping: goals completed or fact limit reached")
                break
                
        except Exception as e:
            print(f"Error in step {step + 1}: {e}")
            break
            
    print(f"\nCompleted with {len(state.facts)} facts")
    return state
