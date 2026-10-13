package rs.runelite.events;

public class ClientStartUp {
   public boolean equals(Object var1) {
      if (var1 == this) {
         return true;
      } else if (!(var1 instanceof ClientStartUp)) {
         return false;
      } else {
         ClientStartUp var2 = (ClientStartUp)var1;
         if (!var2.canEqual(this)) {
            return false;
         }
         return true;
      }
   }

   protected boolean canEqual(Object var1) {
      return var1 instanceof ClientStartUp;
   }

   public int hashCode() {
      boolean var1 = true;
      return 1;
   }

   public String toString() {
      return "ClientStartUp()";
   }
}
